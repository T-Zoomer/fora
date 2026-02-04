from django.contrib import admin

from .models import Question, Answer


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'order']
    list_editable = ['order']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['question', 'text', 'created_at']
    list_filter = ['question', 'created_at']
