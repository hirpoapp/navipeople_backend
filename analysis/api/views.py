import json
from django.http import HttpResponse as HTTPResponse

from analysis.models import Answer, Assessment, Function, Invoice, Plan, Question
from analysis.api.serializers import (
    AssessmentResultsSerializer,
    InvoiceSerializer,
    QuestionSerializer,
)
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response


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
