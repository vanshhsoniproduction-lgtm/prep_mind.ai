from django.db import models
from interviews.models import InterviewSession, Question

class Answer(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    transcript = models.TextField(blank=True, null=True)
    ai_feedback = models.TextField(blank=True, null=True)
    confidence_score = models.IntegerField(null=True, blank=True)
    filler_words = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f"Answer to Q{self.question.order}"
