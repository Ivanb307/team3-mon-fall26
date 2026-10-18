from django.conf import settings
from django.db import models

from parks.models import Borough


class ProfileSkillLevel(models.TextChoices):
    BEGINNER = 'beginner', 'Beginner / Casual'
    INTERMEDIATE = 'intermediate', 'Intermediate'
    COMPETITIVE = 'competitive', 'Competitive'


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    home_borough = models.CharField(max_length=1, choices=Borough.choices, blank=True)
    favorite_sports = models.JSONField(default=list, blank=True)
    skill_level = models.CharField(max_length=16, choices=ProfileSkillLevel.choices, blank=True)

    def __str__(self):
        return f'{self.user.username} profile'
