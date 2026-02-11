from django.contrib import admin

from .models import Question, Answer, Respondent


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'order']
    list_editable = ['order']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['question', 'respondent', 'text', 'created_at']
    list_filter = ['question', 'respondent', 'created_at']


@admin.register(Respondent)
class RespondentAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'created_at']
    readonly_fields = ['uuid', 'created_at']
