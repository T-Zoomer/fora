from django.db import models

from interview.models import Topic


class Result(models.Model):
    topic = models.OneToOneField(Topic, on_delete=models.CASCADE)

    # AI summary
    summary = models.TextField(blank=True, default='')

    # Thematic coding results
    themes = models.JSONField(default=list)  # [{name, description, answer_ids}, ...]
    proposed_themes = models.JSONField(default=list)  # [{name, description}] user-editable, from Pass 1

    # Sentiment results
    sentiment = models.JSONField(default=dict)  # {average: 0.65, answers: [{id, score}, ...]}

    # Metadata
    analyzed_at = models.DateTimeField(auto_now=True)
    answer_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='pending')  # pending, running, discovering, editing, classifying, completed, failed

    class Meta:
        db_table = 'analysis_analysisresult'

    def __str__(self):
        return f"Result for: {self.topic}"
