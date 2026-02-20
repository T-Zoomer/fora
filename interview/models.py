from django.db import models


class Respondent(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Respondent {self.id}"


class Topic(models.Model):
    name = models.TextField()
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
    respondent = models.ForeignKey(Respondent, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer to: {self.topic}"
