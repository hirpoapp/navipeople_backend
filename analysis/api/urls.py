from django.urls import path

from .views import *

urlpatterns = [
    path("create-functions/", create_functions, name="create_functions"),
    path("create-questions/", create_questions, name="create_questions"),
    path("invoice/", InvoiceView.as_view(), name="invoice"),
    path("questions/<str:invoice_uid>", QuestionsView.as_view(), name="questions"),
    path("start/<str:invoice_uid>", AnswerView.as_view(), name="submit_answers"),
    path("result/<str:invoice_uid>", ResultsView.as_view(), name="results"),
    path(
        "export/<str:invoice_uid>", DownloadResultsView.as_view(), name="export_results"
    ),
    path("export-results/<str:invoice_uid>", ExportAnswersView.as_view(), name="export_results"),
]
