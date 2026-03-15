from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    # Additional fields specific to PrepMind AI
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    target_role = models.CharField(max_length=100, null=True, blank=True)
    experience_level = models.CharField(max_length=50, null=True, blank=True)
    
    def __str__(self):
        return self.email or self.username
