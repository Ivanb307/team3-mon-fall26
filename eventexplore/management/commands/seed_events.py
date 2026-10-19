"""Fill the database with fake events for local testing.

Usage:
    python manage.py seed_events            # add sample events
    python manage.py seed_events --clear    # delete all events first, then add
"""
import random
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from eventexplore.models import Event, Registration

A = Event.ActivityType

# (title, activity, location, day offset from today, start hour, start minute,
#  length in minutes, capacity, spots already taken, description)
SAMPLE_EVENTS = [
    ("Saturday Pickup Soccer", A.SOCCER, "Prospect Park Long Meadow, Brooklyn", 1, 10, 0, 120, 22, 18,
     "Casual 11v11 on the Long Meadow. Bring a light and a dark shirt. All levels welcome."),
    ("Reservoir Loop Run", A.RUNNING, "Central Park Reservoir, Manhattan", 1, 7, 30, 60, 30, 12,
     "One lap of the 1.58-mile reservoir loop, conversational pace. Optional second lap."),
    ("West 4th Street Hoops", A.BASKETBALL, "West 4th Street Courts, Manhattan", 2, 14, 0, 150, 15, 14,
     "Competitive half-court runs, winners stay on. Arrive early to get on a team."),
    ("Sunset Vinyasa Flow", A.YOGA, "Sheep Meadow, Central Park, Manhattan", 2, 18, 0, 60, 25, 9,
     "Gentle outdoor flow as the sun goes down. Bring your own mat and water."),
    ("Ultimate Frisbee Scrimmage", A.OTHER, "Flushing Meadows Corona Park, Queens", 3, 16, 0, 120, 20, 7,
     "Co-ed pickup ultimate. Discs and cones provided. Cleats recommended."),
    ("Beginner Tennis Doubles", A.TENNIS, "Riverside Park Tennis Courts, Manhattan", 4, 9, 0, 90, 8, 8,
     "Friendly doubles rotation for newer players. A few spare rackets available."),
    ("Hudson River Greenway Ride", A.CYCLING, "Pier 84, Hudson River Park, Manhattan", 5, 8, 0, 150, 18, 5,
     "No-drop group ride north to the George Washington Bridge and back, about 20 miles. Helmets required."),
    ("Beach Volleyball Social", A.VOLLEYBALL, "Rockaway Beach 97th Street, Queens", 6, 13, 0, 180, 16, 11,
     "Rotating 4v4 games on the sand, then a swim. Sunscreen strongly advised."),
    ("Van Cortlandt Trail Hike", A.HIKING, "Van Cortlandt Park, The Bronx", 7, 9, 30, 180, 15, 4,
     "Easy-to-moderate 5-mile loop through the Northwest Forest and John Muir trails."),
    ("After-Work Basketball", A.BASKETBALL, "McCarren Park Courts, Brooklyn", 8, 18, 30, 120, 12, 3,
     "Full-court 5v5 after work. Mixed skill levels, good vibes."),
    ("Staten Island Greenbelt Hike", A.HIKING, "Staten Island Greenbelt, High Rock Park", 9, 10, 0, 210, 20, 6,
     "Wooded trails, ponds and a climb up Moses Mountain. Wear sturdy shoes."),
    ("Morning Tennis Drills", A.TENNIS, "Fort Greene Park Courts, Brooklyn", 10, 7, 0, 75, 6, 2,
     "Intermediate drills: serves, volleys and baseline rallies."),
    ("Prospect Park Loop Run", A.RUNNING, "Grand Army Plaza, Brooklyn", 11, 8, 0, 60, 40, 21,
     "One 3.35-mile loop of Prospect Park, pace groups from 8 to 11 min/mile."),
    ("Bronx Pickup Soccer", A.SOCCER, "Pelham Bay Park Fields, The Bronx", 12, 11, 0, 120, 22, 10,
     "7v7 small-sided games. Shin guards recommended."),
    ("Yoga by the Water", A.YOGA, "Brooklyn Bridge Park Pier 6, Brooklyn", 14, 9, 0, 60, 20, 20,
     "All-levels flow with skyline views. This one fills up fast."),
    ("Volleyball Night", A.VOLLEYBALL, "Chelsea Park, Manhattan", 16, 19, 0, 120, 12, 5,
     "Indoor-style 6v6 under the lights. Intermediate level."),
    ("Long Island City Bike Tour", A.CYCLING, "Gantry Plaza State Park, Queens", 20, 9, 0, 120, 15, 1,
     "Relaxed ride along the Queens waterfront with stops for photos."),
    # Past events: hidden by default, visible with "Include past events"
    ("Last Week's Pickup Soccer", A.SOCCER, "Prospect Park Long Meadow, Brooklyn", -6, 10, 0, 120, 22, 22,
     "Already happened. Used to check that past events are hidden by default."),
    ("Old Reservoir Run", A.RUNNING, "Central Park Reservoir, Manhattan", -3, 7, 30, 60, 30, 17,
     "Already happened. Used to check that past events are hidden by default."),
]


BOROUGH_KEYWORDS = [
    ("Staten Island", Event.Borough.STATEN_ISLAND),
    ("Bronx", Event.Borough.BRONX),
    ("Brooklyn", Event.Borough.BROOKLYN),
    ("Queens", Event.Borough.QUEENS),
    ("Manhattan", Event.Borough.MANHATTAN),
]


def borough_for(location):
    for keyword, borough in BOROUGH_KEYWORDS:
        if keyword in location:
            return borough
    return ""


class Command(BaseCommand):
    help = "Create fake events (and fake participants) for local development."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Delete all existing events first.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = Event.objects.all().delete()
            self.stdout.write(f"Deleted {deleted} existing rows.")

        User = get_user_model()
        max_taken = max(row[8] for row in SAMPLE_EVENTS)
        players = []
        for i in range(1, max_taken + 1):
            user, created = User.objects.get_or_create(username=f"sample_player_{i:02d}")
            if created:
                user.set_unusable_password()
                user.save()
            players.append(user)

        host, created = User.objects.get_or_create(username="sample_organizer")
        if created:
            host.set_unusable_password()
            host.save()

        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        created_count = 0

        for (title, activity, location, day, hour, minute, length,
             capacity, taken, description) in SAMPLE_EVENTS:
            start = timezone.make_aware(
                datetime.combine(today + timedelta(days=day), time(hour, minute)), tz
            )
            event = Event.objects.create(
                title=title,
                activity_type=activity,
                location=location,
                borough=borough_for(location),
                description=description,
                start_time=start,
                end_time=start + timedelta(minutes=length),
                capacity=capacity,
                host=host,
            )
            for user in random.sample(players, min(taken, capacity)):
                Registration.objects.create(event=event, user=user)
            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Created {created_count} events ({sum(1 for r in SAMPLE_EVENTS if r[3] < 0)} in the past)."
        ))
