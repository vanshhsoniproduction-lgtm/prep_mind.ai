from django.db import models
from django.conf import settings

class InterviewSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=200)
    company_mode = models.CharField(max_length=100, default='General')
    personality_mode = models.CharField(max_length=100, default='Friendly')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, default='In Progress')

    stage = models.CharField(max_length=50, default='tech1')
    question_count = models.IntegerField(default=0)

    technical_score = models.IntegerField(null=True, blank=True)
    communication_score = models.IntegerField(null=True, blank=True)
    confidence_score = models.IntegerField(null=True, blank=True)
    feedback_text = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s {self.role} Interview"

class Question(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    is_coding = models.BooleanField(default=False)
    order = models.IntegerField(default=1)

    def __str__(self):
        return f"Q{self.order} for {self.session.id}"
