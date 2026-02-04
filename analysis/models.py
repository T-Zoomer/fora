from django.db import models

from questions.models import Question


class AnalysisResult(models.Model):
    question = models.OneToOneField(Question, on_delete=models.CASCADE)

    # Thematic coding results
    themes = models.JSONField(default=list)  # [{name, description, answer_ids}, ...]

    # Sentiment analysis results
    sentiment = models.JSONField(default=dict)  # {average: 0.65, answers: [{id, score}, ...]}

    # Metadata
    analyzed_at = models.DateTimeField(auto_now=True)
    answer_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='pending')  # pending, running, completed, failed

    def __str__(self):
        return f"Analysis for: {self.question}"
