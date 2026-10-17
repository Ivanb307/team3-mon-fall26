from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse

CAPACITY_ERROR_MESSAGE = 'Participant limit must be at least 1 or left blank for unlimited.'


class SkillLevel(models.TextChoices):
    ALL = 'all', 'All skill levels'
    BEGINNER = 'beginner', 'Beginner / Casual'
    INTERMEDIATE = 'intermediate', 'Intermediate'
    COMPETITIVE = 'competitive', 'Competitive'


class EventStatus(models.TextChoices):
    SCHEDULED = 'scheduled', 'Scheduled'
    CANCELLED = 'cancelled', 'Cancelled'


class Event(models.Model):
    """Public recreational meetup tied to an NYC park (#22, #24)."""

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organized_events',
    )
    park = models.ForeignKey(
        'parks.Park',
        on_delete=models.PROTECT,
        related_name='events',
    )
    activity = models.CharField(max_length=100, db_index=True)
    date = models.DateField(db_index=True)
    time = models.TimeField()
    skill_level = models.CharField(
        max_length=32,
        choices=SkillLevel.choices,
        default=SkillLevel.ALL,
    )
    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1, message=CAPACITY_ERROR_MESSAGE)],
        help_text='Optional maximum number of participants. Leave blank for unlimited.',
    )
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.SCHEDULED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'time', 'id']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(capacity__isnull=True) | models.Q(capacity__gte=1),
                name='event_capacity_at_least_1',
            ),
        ]

    @property
    def owner(self):
        return self.organizer

    def get_absolute_url(self):
        return reverse('event_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return f'{self.activity} at {self.park.name} ({self.date})'

