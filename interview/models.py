import uuid

from django.db import models


class Interview(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=200)
    intro_message = models.TextField(
        blank=True,
        default='',
        help_text="Opening message shown to the respondent at the start of the interview.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_open = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class InterviewSession(models.Model):
    interview = models.ForeignKey(
        Interview, on_delete=models.CASCADE, null=True, related_name='sessions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.id}"


class Topic(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=500)
    goal = models.TextField(
        blank=True,
        default='',
        help_text=(
            "What you want to find out from respondents. "
            "Used to guide the interview questions and to judge whether the topic has been sufficiently covered."
        ),
    )
    order = models.PositiveIntegerField(default=0)
    analyze_sentiment = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name[:50]


class Answer(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('topic', 'session')]

    def __str__(self):
        return f"Answer to: {self.topic}"
