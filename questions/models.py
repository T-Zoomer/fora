import uuid

from django.db import models


class Respondent(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.uuid)[:8]


class Question(models.Model):
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)
    analyze_sentiment = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text[:50]


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    respondent = models.ForeignKey(Respondent, on_delete=models.CASCADE, null=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer to: {self.question}"
