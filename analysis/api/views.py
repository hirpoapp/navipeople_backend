import json

from django.http import HttpResponse as HTTPResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .utils import queryset_to_xlxs

from analysis.api.serializers import (
    AssessmentResultsSerializer,
    InvoiceSerializer,
    QuestionSerializer,
    AnswerSerializer,
)
from analysis.models import Answer, Assessment, Function, Invoice, Plan, Question

# JSON-u oxumaq (məsələn fayldan)
with open("json/questions.json", "r", encoding="utf-8") as f:
    data = json.load(f)


def create_functions(request):
    for item in data["functions"]:
        Function.objects.create(
            az=item["name"]["az"], en=item["name"]["en"], ru=item["name"]["ru"]
        )
    return HTTPResponse("Functions created successfully.")


def create_questions(request):
    """
    Bulk-create Question records from `data["questions"]`, associate them with Plans,
    and return a success response. Assumes `data` is available in scope.
    """
    for item in data["questions"]:
        # Fetch related Function and Plans
        function = Function.objects.get(id=item["function_id"])
        plans = Plan.objects.filter(name__in=item["type"])

        # Extract multilingual fields
        name = item["question"]

        # Create the Question and set its many-to-many Plans
        question = Question.objects.create(
            function=function,
            az=name["az"],
            en=name["en"],
            ru=name["ru"],
            priority=item["priority"],
        )
        # The instance returned by .create() is already saved; an extra .save() is unnecessary.
        question.plan.set(plans)

    return HTTPResponse("Functions created successfully.")


class InvoiceView(APIView):
    def post(self, request):
        serializer = InvoiceSerializer(data=request.data)
        if serializer.is_valid():
            invoice = serializer.save()
            return Response({"uid": invoice.uid}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class QuestionsView(APIView):
    def get(self, request, invoice_uid):
        try:
            invoice = Invoice.objects.get(uid=invoice_uid)
        except Invoice.DoesNotExist:
            return Response(
                {"error": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND
            )

        plan = invoice.plan
        questions = (
            Question.objects.filter(plan=plan)
            .select_related("function")
            .order_by("-function__id", "id")
        )

        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AnswerView(APIView):
    def post(self, request, invoice_uid):
        answers = request.data
        answer_queryset = []
        for answer_map in answers:
            if "question_id" in answer_map and "answer_id" in answer_map:
                question_id = answer_map["question_id"]
                answer_id = answer_map["answer_id"]
            else:
                question_id, answer_id = next(iter(answer_map.items()))

            answer_queryset.append(
                Answer(
                    invoice_id=Invoice.objects.get(uid=invoice_uid).id,
                    question_id=question_id,
                    response=answer_id,
                )
            )

        Answer.objects.bulk_create(answer_queryset)
        Assessment.objects.update_or_create(
            invoice_id=Invoice.objects.get(uid=invoice_uid).id,
            defaults={"is_completed": True},
        )
        return Response({"status": "Answers received."}, status=status.HTTP_200_OK)


class ResultsView(APIView):
    def get(self, request, invoice_uid):
        try:
            invoice = Invoice.objects.get(uid=invoice_uid)
            assessment = Assessment.objects.get(invoice=invoice)
        except (Invoice.DoesNotExist, Assessment.DoesNotExist):
            return Response(
                {"error": "Invoice or Assessment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AssessmentResultsSerializer(assessment)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DownloadResultsView(APIView):
    def get(self, request, invoice_uid):
        """
        Retrieve assessment results for the given invoice and return them as an XLSX file.
        Returns 404 if either the Invoice or its Assessment does not exist.
        """
        try:
            invoice = Invoice.objects.get(uid=invoice_uid)
            assessment = Assessment.objects.get(invoice=invoice)
        except (Invoice.DoesNotExist, Assessment.DoesNotExist):
            return Response(
                {"error": "Invoice or Assessment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AssessmentResultsSerializer(assessment)
        rows = []
        results = serializer.data.get("functions") or []
        for result in results:
            distribution = result.get("distribution") or {}
            function_name_value = result.get("function_name")
            function_name = (
                function_name_value.get("en", "")
                if isinstance(function_name_value, dict)
                else (function_name_value or "")
            )

            row = {
                "Function Name": function_name,
                "Total Questions": result.get("total_questions", 0),
                "Not Applicable": distribution.get("1", 0),
                "Not Implemented": distribution.get("2", 0),
                "Partially Implemented": distribution.get("3", 0),
                "Implemented and Functioning": distribution.get("4", 0),
                "Systematic and Innovative Implementation": distribution.get("5", 0),
                "Result": result.get("total_score", 0),
            }
            rows.append(row)

        return queryset_to_xlxs(rows, f"diagnosis_results_{invoice_uid}.xlsx")


class ExportAnswersView(APIView):
    def get(self, request, invoice_uid):
        try:
            invoice = Invoice.objects.get(uid=invoice_uid)
        except Invoice.DoesNotExist:
            return Response({"error": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)

        answers = (
            Answer.objects.filter(invoice=invoice)
            .select_related("question__function")
            .order_by("-question__function__id", "question__id")
        )

        rows = [
            {
                "Question": getattr(a.question, "en", "") if a.question else "",
                "Function": getattr(a.question.function, "en", "") if (a.question and a.question.function) else "",
                "Answer": a.get_response_display(),
            }
            for a in answers
        ]

        filename = f"answers_{invoice_uid}.xlsx"
        return queryset_to_xlxs(rows, filename)
