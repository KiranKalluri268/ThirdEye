from django.db import models
from django.utils import timezone
from accounts.models import CustomUser


class LearningSession(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def check_expiry(self):
        """
        Marks the session as expired if it hasn't been started within a grace period
        of 30 minutes after the scheduled start time.
        """
        if self.status == 'scheduled':
            grace_period = timezone.timedelta(minutes=30)
            if timezone.now() > (self.start_time + grace_period):
                self.status = 'expired'
                self.save()
                return True
        return False


class SessionEnrollment(models.Model):
    session = models.ForeignKey(LearningSession, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['session', 'student']


class EngagementRecord(models.Model):
    ENGAGEMENT_LEVELS = [
        ('very_low', 'Very Low'),
        ('low', 'Low'),
        ('high', 'High'),
        ('very_high', 'Very High'),
    ]
    session = models.ForeignKey(LearningSession, on_delete=models.CASCADE, related_name='engagement_records')
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='engagement_records')
    engagement_level = models.CharField(max_length=20, choices=ENGAGEMENT_LEVELS)
    confidence_score = models.FloatField(default=0.0)
    model_used = models.CharField(max_length=50, default='hybrid_ensemble')
    timestamp = models.DateTimeField(auto_now_add=True)
    frame_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.username} - {self.engagement_level}"
