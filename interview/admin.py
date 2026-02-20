from django.contrib import admin

from .models import Topic, Answer, Respondent


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'analyze_sentiment']
    list_editable = ['order', 'analyze_sentiment']
    fields = ['name', 'goal', 'order', 'analyze_sentiment']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['topic', 'respondent', 'text', 'created_at']
    list_filter = ['topic', 'respondent', 'created_at']


@admin.register(Respondent)
class RespondentAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at']
    readonly_fields = ['created_at']
