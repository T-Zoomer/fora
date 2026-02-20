from django.contrib import admin

from .models import Interview, Topic, Answer, Respondent


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    fields = ['name', 'intro_message']


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'interview', 'order', 'analyze_sentiment']
    list_editable = ['order', 'analyze_sentiment']
    list_filter = ['interview']
    fields = ['interview', 'name', 'goal', 'order', 'analyze_sentiment']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['topic', 'respondent', 'text', 'created_at']
    list_filter = ['topic', 'respondent', 'created_at']


@admin.register(Respondent)
class RespondentAdmin(admin.ModelAdmin):
    list_display = ['id', 'interview', 'created_at']
    readonly_fields = ['created_at']
