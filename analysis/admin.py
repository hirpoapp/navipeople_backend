from django.contrib import admin
from .models import Plan, Invoice, Function, Question, Answer, Assessment

# Register your models here.
admin.site.register(Plan)
admin.site.register(Invoice)
admin.site.register(Function)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Assessment)
