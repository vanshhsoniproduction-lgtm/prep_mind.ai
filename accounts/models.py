from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    # Additional fields specific to PrepMind AI
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    target_role = models.CharField(max_length=100, null=True, blank=True)
    experience_level = models.CharField(max_length=50, null=True, blank=True)
    interview_credits = models.IntegerField(default=3)
    
    # HR specific fields
    is_hr = models.BooleanField(default=False)
    company_name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    hr_credits = models.IntegerField(default=0)
    
    def __str__(self):
        return self.email or self.username

class HRUnlockedCandidate(models.Model):
    hr_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='unlocked_candidates_by_hr')
    candidate = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='unlocked_by_hrs')
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('hr_user', 'candidate')

class HRInterviewRequest(models.Model):
    hr_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_interview_requests')
    candidate = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_interview_requests')
    note = models.TextField(blank=True, null=True)
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.TimeField(null=True, blank=True)
    
    is_read_by_candidate = models.BooleanField(default=False)
    is_read_by_hr = models.BooleanField(default=True) # Usually the sender doesn't need to read their own, but maybe candidate replies later?
    status = models.CharField(max_length=20, default='Pending') # Pending, Accepted, Declined
    
    created_at = models.DateTimeField(auto_now_add=True)
