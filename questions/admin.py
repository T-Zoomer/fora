from django.contrib import admin

from .models import Interview, Answer, Respondent


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['text', 'order']
    list_editable = ['order']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['interview', 'respondent', 'text', 'created_at']
    list_filter = ['interview', 'respondent', 'created_at']


@admin.register(Respondent)
class RespondentAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'created_at']
    readonly_fields = ['uuid', 'created_at']
