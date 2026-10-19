from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Event, Registration


def make_event(**overrides):
    start = overrides.pop("start_time", timezone.now() + timedelta(days=2))
    defaults = {
        "title": "Pickup Basketball",
        "activity_type": Event.ActivityType.BASKETBALL,
        "description": "Friendly 5v5 games, all levels welcome.",
        "location": "Tompkins Square Park",
        "borough": Event.Borough.MANHATTAN,
        "start_time": start,
        "end_time": start + timedelta(hours=2),
        "capacity": 10,
    }
    defaults.update(overrides)
    return Event.objects.create(**defaults)


class EventQuerySetTests(TestCase):
    def test_upcoming_excludes_past_unpublished_and_private(self):
        upcoming = make_event(title="Upcoming")
        make_event(title="Past", start_time=timezone.now() - timedelta(days=1))
        make_event(title="Draft", is_published=False)
        make_event(title="Private", is_public=False)

        self.assertEqual(list(Event.objects.upcoming()), [upcoming])

    def test_upcoming_ordered_soonest_first(self):
        later = make_event(title="Later", start_time=timezone.now() + timedelta(days=5))
        sooner = make_event(title="Sooner", start_time=timezone.now() + timedelta(days=1))

        self.assertEqual(list(Event.objects.upcoming()), [sooner, later])

    def test_remaining_spots_uses_registrations(self):
        event = make_event(capacity=3)
        User = get_user_model()
        for name in ("a", "b"):
            Registration.objects.create(event=event, user=User.objects.create_user(username=name))

        annotated = Event.objects.with_capacity().get(pk=event.pk)
        self.assertEqual(annotated.taken_count, 2)
        self.assertEqual(annotated.remaining_spots, 1)
        self.assertFalse(annotated.is_full)

        Registration.objects.create(event=event, user=User.objects.create_user(username="c"))
        self.assertTrue(Event.objects.with_capacity().get(pk=event.pk).is_full)


class EventListViewTests(TestCase):
    def test_feed_shows_upcoming_event_fields(self):
        event = make_event(capacity=12)

        response = self.client.get(reverse("eventexplore:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, event.title)
        self.assertContains(response, "Basketball")
        self.assertContains(response, event.location)
        self.assertContains(response, "12 spots left")
        self.assertContains(response, "0 of 12 going")
        self.assertContains(response, event.get_absolute_url())

    def test_feed_excludes_past_events_by_default(self):
        make_event(title="Old Run", start_time=timezone.now() - timedelta(days=3))
        make_event(title="New Run")

        response = self.client.get(reverse("eventexplore:list"))

        self.assertContains(response, "New Run")
        self.assertNotContains(response, "Old Run")

    def test_include_past_shows_past_events(self):
        make_event(title="Old Run", start_time=timezone.now() - timedelta(days=3))

        response = self.client.get(reverse("eventexplore:list"), {"include_past": "1"})

        self.assertContains(response, "Old Run")
        self.assertContains(response, "Event ended")

    def test_activity_filter(self):
        make_event(title="Morning Yoga", activity_type=Event.ActivityType.YOGA)
        make_event(title="Hoops")

        response = self.client.get(reverse("eventexplore:list"), {"activity": "yoga"})

        self.assertContains(response, "Morning Yoga")
        self.assertNotContains(response, "Hoops")

    def test_empty_state(self):
        response = self.client.get(reverse("eventexplore:list"))
        self.assertContains(response, "No upcoming events")

    def test_feed_available_to_authenticated_users(self):
        user = get_user_model().objects.create_user(username="sam", password="pw12345!")
        self.client.force_login(user)
        make_event()

        response = self.client.get(reverse("eventexplore:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pickup Basketball")


class EventDetailViewTests(TestCase):
    def test_detail_shows_full_information(self):
        event = make_event(capacity=8)

        response = self.client.get(event.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "eventexplore/event_detail.html")
        self.assertContains(response, event.title)
        self.assertContains(response, event.description)
        self.assertContains(response, event.location)
        self.assertContains(response, "8 spots left")

    def test_detail_shows_full_status(self):
        event = make_event(capacity=1)
        Registration.objects.create(
            event=event, user=get_user_model().objects.create_user(username="x")
        )

        response = self.client.get(event.get_absolute_url())

        self.assertContains(response, "Full")

    def test_feed_links_to_detail_page(self):
        event = make_event()
        feed = self.client.get(reverse("eventexplore:list"))
        self.assertContains(feed, f'href="{event.get_absolute_url()}"')

    def test_unpublished_or_private_event_returns_404(self):
        draft = make_event(is_published=False)
        private = make_event(is_public=False)

        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(private.get_absolute_url()).status_code, 404)


class EventApiTests(TestCase):
    def test_upcoming_api_returns_capacity_metrics(self):
        event = make_event(capacity=5)
        Registration.objects.create(
            event=event, user=get_user_model().objects.create_user(username="r")
        )
        make_event(title="Past", start_time=timezone.now() - timedelta(days=1))

        response = self.client.get(reverse("eventexplore:api_upcoming"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        item = data["results"][0]
        self.assertEqual(item["id"], event.pk)
        self.assertEqual(item["activity_type"], "basketball")
        self.assertEqual(item["capacity"], 5)
        self.assertEqual(item["spots_taken"], 1)
        self.assertEqual(item["remaining_spots"], 4)
        self.assertFalse(item["is_full"])

    def test_detail_api(self):
        event = make_event()

        data = self.client.get(reverse("eventexplore:api_detail", args=[event.pk])).json()

        self.assertEqual(data["title"], event.title)
        self.assertEqual(data["description"], event.description)
        self.assertFalse(data["is_past"])

    def test_api_rejects_post(self):
        response = self.client.post(reverse("eventexplore:api_upcoming"))
        self.assertEqual(response.status_code, 405)


class BoroughFilterTests(TestCase):
    def test_borough_filter_on_feed(self):
        make_event(title="Brooklyn Run", borough=Event.Borough.BROOKLYN)
        make_event(title="Manhattan Hoops", borough=Event.Borough.MANHATTAN)

        response = self.client.get(reverse("eventexplore:list"), {"borough": "brooklyn"})

        self.assertContains(response, "Brooklyn Run")
        self.assertNotContains(response, "Manhattan Hoops")

    def test_borough_and_activity_filters_combine(self):
        make_event(title="Queens Yoga", borough=Event.Borough.QUEENS, activity_type=Event.ActivityType.YOGA)
        make_event(title="Queens Hoops", borough=Event.Borough.QUEENS)
        make_event(title="Bronx Yoga", borough=Event.Borough.BRONX, activity_type=Event.ActivityType.YOGA)

        response = self.client.get(reverse("eventexplore:list"), {"borough": "queens", "activity": "yoga"})

        self.assertContains(response, "Queens Yoga")
        self.assertNotContains(response, "Queens Hoops")
        self.assertNotContains(response, "Bronx Yoga")

    def test_unknown_borough_is_ignored(self):
        make_event(title="Anywhere Event")

        response = self.client.get(reverse("eventexplore:list"), {"borough": "atlantis"})

        self.assertContains(response, "Anywhere Event")

    def test_borough_filter_on_api(self):
        make_event(title="SI Hike", borough=Event.Borough.STATEN_ISLAND)
        make_event(title="Manhattan Run")

        data = self.client.get(reverse("eventexplore:api_upcoming"), {"borough": "staten_island"}).json()

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["borough_label"], "Staten Island")

    def test_detail_shows_borough_and_capacity_bar(self):
        event = make_event(borough=Event.Borough.BRONX, capacity=4)
        Registration.objects.create(event=event, user=get_user_model().objects.create_user(username="z"))

        response = self.client.get(event.get_absolute_url())

        self.assertContains(response, "The Bronx")
        self.assertContains(response, 'value="1" max="4"')
        self.assertContains(response, "25% full")

    def test_bar_and_text_agree_for_nearly_full_event(self):
        event = make_event(capacity=22)
        User = get_user_model()
        for i in range(18):
            Registration.objects.create(event=event, user=User.objects.create_user(username=f"p{i}"))

        feed = self.client.get(reverse("eventexplore:list"))
        self.assertContains(feed, "4 spots left")
        self.assertContains(feed, "18 of 22 going")
        self.assertContains(feed, 'value="18" max="22"')

        detail = self.client.get(event.get_absolute_url())
        self.assertContains(detail, "18 of 22 going · 82% full")
