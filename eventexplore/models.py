from django.conf import settings
from django.db import models
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone


class EventQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True, is_public=True)

    def upcoming(self):
        """Published, public events that have not started yet, soonest first."""
        return self.published().filter(start_time__gte=timezone.now()).order_by("start_time")

    def with_capacity(self):
        """Annotate each event with how many spots are taken."""
        return self.annotate(spots_taken=Count("registrations", distinct=True))


class Event(models.Model):
    class ActivityType(models.TextChoices):
        BASKETBALL = "basketball", "Basketball"
        SOCCER = "soccer", "Soccer"
        RUNNING = "running", "Running"
        CYCLING = "cycling", "Cycling"
        YOGA = "yoga", "Yoga"
        HIKING = "hiking", "Hiking"
        TENNIS = "tennis", "Tennis"
        VOLLEYBALL = "volleyball", "Volleyball"
        OTHER = "other", "Other"

    class Borough(models.TextChoices):
        MANHATTAN = "manhattan", "Manhattan"
        BROOKLYN = "brooklyn", "Brooklyn"
        QUEENS = "queens", "Queens"
        BRONX = "bronx", "The Bronx"
        STATEN_ISLAND = "staten_island", "Staten Island"

    title = models.CharField(max_length=200)
    activity_type = models.CharField(max_length=30, choices=ActivityType.choices)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255)
    borough = models.CharField(max_length=20, choices=Borough.choices, blank=True, default="")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    is_public = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hosted_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = EventQuerySet.as_manager()

    class Meta:
        ordering = ["start_time"]
        indexes = [models.Index(fields=["is_published", "is_public", "start_time"])]

    def __str__(self):
        return f"{self.title} ({self.start_time:%Y-%m-%d %H:%M})"

    def get_absolute_url(self):
        return reverse("eventexplore:detail", args=[self.pk])

    @property
    def taken_count(self):
        # Use the annotated value when the queryset provided it, otherwise count.
        taken = getattr(self, "spots_taken", None)
        return taken if taken is not None else self.registrations.count()

    @property
    def remaining_spots(self):
        return max(self.capacity - self.taken_count, 0)

    @property
    def percent_full(self):
        if not self.capacity:
            return 100
        return min(round(self.taken_count * 100 / self.capacity), 100)

    @property
    def is_full(self):
        return self.remaining_spots == 0

    @property
    def is_past(self):
        return self.start_time < timezone.now()


class Registration(models.Model):
    """A user holding a spot at an event. Used to compute remaining capacity."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="event_registrations"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "user"], name="unique_registration")
        ]

    def __str__(self):
        return f"{self.user} → {self.event}"
