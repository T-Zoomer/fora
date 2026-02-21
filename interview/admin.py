from django.contrib import admin

from .models import Interview, Topic, Answer, InterviewSession


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ['session', 'text', 'created_at']
    can_delete = False
    show_change_link = False


class TopicInline(admin.StackedInline):
    model = Topic
    extra = 0
    fields = ['name', 'goal', 'order', 'analyze_sentiment']
    ordering = ['order']
    show_change_link = True


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_open', 'created_at']
    fields = ['name', 'intro_message', 'is_open']
    inlines = [TopicInline]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'interview', 'order', 'analyze_sentiment']
    list_editable = ['order', 'analyze_sentiment']
    list_filter = ['interview']
    fields = ['interview', 'name', 'goal', 'order', 'analyze_sentiment']
    inlines = [AnswerInline]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['session', 'topic', 'text', 'created_at']
    list_filter = ['topic__interview', 'topic']
    readonly_fields = ['topic', 'session', 'text', 'created_at']


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'interview', 'created_at']
    readonly_fields = ['created_at']
