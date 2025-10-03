from rest_framework import serializers

from analysis.api.utils import build_assessment_results
from analysis.models import Answer, Function, Invoice, Question


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = "__all__"


class FunctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Function
        fields = "__all__"


class QuestionSerializer(serializers.ModelSerializer):
    function = FunctionSerializer()
    answer = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = "__all__"

    def get_answer(self, obj):
        answer = Answer.objects.filter(
            question=obj, invoice__uid=self.context.get("invoice_uid")
        ).first()
        return answer.response if answer else None


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["question"] = QuestionSerializer(instance.question).data
        return representation


class AssessmentResultsSerializer(serializers.Serializer):
    def to_representation(self, assessment):
        return build_assessment_results(assessment)
