import io
from collections import Counter
from typing import Dict, List

import pandas as pd
from django.http import HttpResponse

from analysis.choices import ANSWERS_CHOICES
from analysis.models import Function

SCORE_MAP: Dict[int, int] = {1: 0, 2: 25, 3: 50, 4: 75, 5: 100}
SENTIMENT_MAP: Dict[int, str] = {
    1: "negative",
    2: "negative",
    3: "neutral",
    4: "positive",
    5: "positive",
}
SENTIMENT_ORDER: List[str] = ["negative", "neutral", "positive"]


def _ensure_plan_functions(assessment):
    invoice = assessment.invoice
    plan_functions = {
        function.id: function
        for function in Function.objects.filter(questions__plan=invoice.plan).distinct()
    }

    per_function_data = {
        function_id: {
            "function": plan_function,
            "counts": Counter(),
            "total_answers": 0,
            "question_count": plan_function.questions.filter(plan=invoice.plan)
            .distinct()
            .count(),
        }
        for function_id, plan_function in plan_functions.items()
    }

    return plan_functions, per_function_data


def build_assessment_results(assessment):
    answer_scale = [value for value, _ in ANSWERS_CHOICES]
    plan_functions, per_function_data = _ensure_plan_functions(assessment)

    overall_counts = Counter()
    overall_score_sum = 0
    overall_answers = 0

    for answer in assessment.invoice.answers.select_related("question__function"):
        function = getattr(answer.question, "function", None)
        if function is None:
            continue

        if function.id not in per_function_data:
            plan_functions[function.id] = function
            per_function_data[function.id] = {
                "function": function,
                "counts": Counter(),
                "total_answers": 0,
                "question_count": function.questions.filter(
                    plan=assessment.invoice.plan
                )
                .distinct()
                .count(),
            }

        function_data = per_function_data[function.id]
        function_data["counts"][answer.response] += 1
        function_data["total_answers"] += 1

        overall_counts[answer.response] += 1
        overall_score_sum += SCORE_MAP.get(answer.response, 0)
        overall_answers += 1

    function_results = []
    for function_id in sorted(per_function_data):
        data = per_function_data[function_id]
        function_obj = data["function"]
        total_answers = data["total_answers"]
        question_count = data["question_count"]

        distribution = {
            str(answer_value): (
                round((data["counts"].get(answer_value, 0) / total_answers) * 100, 2)
                if total_answers
                else 0
            )
            for answer_value in answer_scale
        }

        score_sum = sum(
            SCORE_MAP.get(answer_value, 0) * data["counts"].get(answer_value, 0)
            for answer_value in answer_scale
        )
        final_score = round(score_sum / total_answers, 2) if total_answers else 0

        sentiment_counts = {sentiment: 0 for sentiment in SENTIMENT_ORDER}
        for answer_value, count in data["counts"].items():
            if sentiment := SENTIMENT_MAP.get(answer_value):
                sentiment_counts[sentiment] += count

        sentiment_percentages = {
            sentiment: (round((count / total_answers) * 100, 2) if total_answers else 0)
            for sentiment, count in sentiment_counts.items()
        }

        function_results.append(
            {
                "function_name": {
                    "az": function_obj.az,
                    "en": function_obj.en,
                    "ru": function_obj.ru,
                },
                "total_questions": question_count,
                "total_score": final_score,
                "distribution": distribution,
                "sentiment": {
                    "counts": sentiment_counts,
                    "percentages": sentiment_percentages,
                },
            }
        )

    overall_distribution = {
        str(answer_value): (
            round((overall_counts.get(answer_value, 0) / overall_answers) * 100, 2)
            if overall_answers
            else 0
        )
        for answer_value in answer_scale
    }

    overall_sentiment_counts = {sentiment: 0 for sentiment in SENTIMENT_ORDER}
    for answer_value, count in overall_counts.items():
        if sentiment := SENTIMENT_MAP.get(answer_value):
            overall_sentiment_counts[sentiment] += count

    overall_sentiment_percentages = {
        sentiment: (round((count / overall_answers) * 100, 2) if overall_answers else 0)
        for sentiment, count in overall_sentiment_counts.items()
    }

    overall_final_score = (
        round(overall_score_sum / overall_answers, 2) if overall_answers else 0
    )

    return {
        "functions": function_results,
        "overall": {
            "total_questions": sum(
                data["question_count"] for data in per_function_data.values()
            ),
            "total_answers": overall_answers,
            "total_score": overall_final_score,
            "distribution": overall_distribution,
            "sentiment": {
                "counts": overall_sentiment_counts,
                "percentages": overall_sentiment_percentages,
            },
        },
    }


def queryset_to_xlxs(rows, name):
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Performance")

    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f"attachment; filename={name}.xlsx"
    return response
