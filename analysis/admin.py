from django.contrib import admin

from .models import AnalysisResult


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ['question', 'status', 'answer_count', 'analyzed_at']
    list_filter = ['status']
    readonly_fields = ['analyzed_at']
