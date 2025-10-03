from django.db import models

from .choices import PLAN_CHOICES, ANSWERS_CHOICES
import uuid


# Create your models here.
class Plan(models.Model):
    """Abunə planları."""

    name = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    features = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.name


class Invoice(models.Model):
    """Faktura məlumatları."""

    uid = models.UUIDField(unique=True, auto_created=True, default=uuid.uuid4)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="invoices")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    issued_date = models.DateField(auto_now_add=True)
    is_paid = models.BooleanField(default=True)
    email = models.EmailField(null=True, blank=True)

    def __str__(self):
        return f"Invoice {self.id} - {self.plan}"


class Function(models.Model):
    """Məsələn: Performance Management, Corporate Goals və s."""

    az = models.CharField(max_length=255, unique=True, null=True)
    en = models.CharField(max_length=255, unique=True, null=True)
    ru = models.CharField(max_length=255, unique=True, null=True)

    def __str__(self):
        return self.az


class Question(models.Model):
    """Sistem sualları (multilanguage ilə)."""

    function = models.ForeignKey(
        Function, on_delete=models.CASCADE, related_name="questions"
    )
    az = models.TextField()
    en = models.TextField()
    ru = models.TextField()
    priority = models.IntegerField(default=1)
    plan = models.ManyToManyField(Plan, related_name="questions")

    def __str__(self):
        return self.en


class Answer(models.Model):
    """Cavablar."""

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers"
    )
    response = models.IntegerField(choices=ANSWERS_CHOICES)

    def __str__(self):
        return f"Answer to {self.question} - {self.get_response_display()}"


class Assessment(models.Model):
    """Qiymətləndirmə nəticələri."""

    invoice = models.OneToOneField(
        Invoice, on_delete=models.CASCADE, related_name="assessment"
    )
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Assessment for {self.invoice} - Completed: {self.is_completed}"
