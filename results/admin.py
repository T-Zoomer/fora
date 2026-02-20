from django.contrib import admin

from .models import Result


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ['topic', 'status', 'answer_count', 'analyzed_at']
    list_filter = ['status']
    readonly_fields = ['analyzed_at']
