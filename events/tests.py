import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from parks.models import Borough, Park

from .models import CAPACITY_ERROR_MESSAGE, NYC_TZ, Event, EventStatus, SkillLevel

User = get_user_model()
PASSWORD = 'Hudson-River-Run-77'


class EventCreationAndCapacityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('organizer', 'organizer@nyu.edu', PASSWORD)
        self.park = Park.objects.create(
            gispropnum='M110',
            name='William McCray Playground',
            borough=Borough.MANHATTAN,
            address='53-41 WEST 138 STREET',
            is_retired=False,
        )
        self.retired_park = Park.objects.create(
            gispropnum='M999',
            name='Retired Playground',
            borough=Borough.MANHATTAN,
            is_retired=True,
        )
        self.future_date = (timezone.localdate() + datetime.timedelta(days=7)).isoformat()

    def valid_payload(self, **overrides):
        data = {
            'park': self.park.pk,
            'activity': 'Pickup Basketball',
            'date': self.future_date,
            'time': '18:30',
            'skill_level': SkillLevel.INTERMEDIATE,
            'capacity': '10',
            'description': 'Half-court 5v5 run, bring a dark and light shirt.',
        }
        data.update(overrides)
        return data

    def test_unauthenticated_user_is_redirected_to_login(self):
        url = reverse('event_create')
        get_response = self.client.get(url)
        self.assertRedirects(get_response, f"{reverse('login')}?next={url}")

        post_response = self.client.post(url, self.valid_payload())
        self.assertRedirects(post_response, f"{reverse('login')}?next={url}")
        self.assertEqual(Event.objects.count(), 0)

    def test_landing_page_shows_create_event_button_only_when_authenticated(self):
        anon_response = self.client.get(reverse('home'))
        self.assertNotContains(anon_response, f'href="{reverse("event_create")}"')

        self.client.login(username='organizer', password=PASSWORD)
        auth_response = self.client.get(reverse('home'))
        self.assertContains(auth_response, f'href="{reverse("event_create")}"')

    def test_create_event_page_renders_active_parks_in_dropdown(self):
        self.client.login(username='organizer', password=PASSWORD)
        response = self.client.get(reverse('event_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'events/event_form.html')
        self.assertContains(response, 'William McCray Playground (Manhattan)')
        self.assertNotContains(response, 'Retired Playground')

    def test_successful_event_creation_assigns_owner_and_redirects_to_event_page(self):
        self.client.login(username='organizer', password=PASSWORD)
        response = self.client.post(reverse('event_create'), self.valid_payload(), follow=True)

        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.first()
        self.assertRedirects(response, reverse('event_detail', kwargs={'pk': event.pk}))
        self.assertEqual(event.organizer, self.user)
        self.assertEqual(event.owner, self.user)
        self.assertEqual(event.park, self.park)
        self.assertEqual(event.activity, 'Pickup Basketball')
        self.assertEqual(event.skill_level, SkillLevel.INTERMEDIATE)
        self.assertEqual(event.capacity, 10)
        self.assertContains(response, 'Event created and published!')
        self.assertContains(response, 'Pickup Basketball')
        self.assertContains(response, 'William McCray Playground')
        self.assertContains(response, 'organizer')
        self.assertContains(response, '10 participants')

    def test_missing_required_fields_rejected_without_creating_partial_record(self):
        self.client.login(username='organizer', password=PASSWORD)
        for missing_field in ('park', 'activity', 'date', 'time', 'description'):
            with self.subTest(missing_field=missing_field):
                response = self.client.post(
                    reverse('event_create'),
                    self.valid_payload(**{missing_field: ''}),
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(missing_field, response.context['form'].errors)
                self.assertEqual(Event.objects.count(), 0)

    def test_past_date_is_rejected_without_creating_event(self):
        self.client.login(username='organizer', password=PASSWORD)
        past_date = (timezone.localdate() - datetime.timedelta(days=1)).isoformat()
        response = self.client.post(reverse('event_create'), self.valid_payload(date=past_date))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Event date and time must be in the future.')
        self.assertEqual(Event.objects.count(), 0)

    def test_blank_capacity_saves_as_unlimited_and_displays_on_event_page(self):
        self.client.login(username='organizer', password=PASSWORD)
        response = self.client.post(reverse('event_create'), self.valid_payload(capacity=''), follow=True)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.first()
        self.assertIsNone(event.capacity)
        self.assertContains(response, 'Unlimited')

    def test_zero_and_negative_capacity_rejected_with_exact_error_message(self):
        self.client.login(username='organizer', password=PASSWORD)
        for invalid_capacity in ('0', '-1', '-10', 'abc'):
            with self.subTest(capacity=invalid_capacity):
                response = self.client.post(
                    reverse('event_create'),
                    self.valid_payload(capacity=invalid_capacity),
                )
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, CAPACITY_ERROR_MESSAGE)
                self.assertEqual(
                    response.context['form'].errors.get('capacity'),
                    [CAPACITY_ERROR_MESSAGE],
                )
                self.assertEqual(Event.objects.count(), 0)

    def test_whitespace_only_text_fields_and_overflow_capacity_rejected(self):
        self.client.login(username='organizer', password=PASSWORD)
        response = self.client.post(
            reverse('event_create'),
            self.valid_payload(activity='   ', description='   ', capacity='99999999'),
        )
        self.assertEqual(response.status_code, 200)
        errors = response.context['form'].errors
        self.assertIn('activity', errors)
        self.assertIn('description', errors)
        self.assertIn('capacity', errors)
        self.assertEqual(Event.objects.count(), 0)



class EventDiscoveryFeedTests(TestCase):
    """Upcoming event discovery feed and details (#25)."""

    def setUp(self):
        self.organizer = User.objects.create_user('host', 'host@nyu.edu', PASSWORD)
        self.manhattan_park = Park.objects.create(
            gispropnum='M010', name='Central Park', borough=Borough.MANHATTAN, address='Central Park West'
        )
        self.brooklyn_park = Park.objects.create(
            gispropnum='B073', name='Prospect Park', borough=Borough.BROOKLYN
        )
        self.today = timezone.now().astimezone(NYC_TZ).date()

    def make_event(self, days=3, **overrides):
        data = {
            'organizer': self.organizer,
            'park': self.manhattan_park,
            'activity': 'Pickup Basketball',
            'date': self.today + datetime.timedelta(days=days),
            'time': datetime.time(18, 30),
            'skill_level': SkillLevel.ALL,
            'capacity': 10,
            'description': 'Half-court 5v5, all levels.',
        }
        data.update(overrides)
        return Event.objects.create(**data)

    # Queryset

    def test_upcoming_excludes_past_and_cancelled_and_orders_soonest_first(self):
        later = self.make_event(days=5, activity='Later Run')
        sooner = self.make_event(days=1, activity='Sooner Run')
        self.make_event(days=-1, activity='Yesterday Run')
        self.make_event(days=2, activity='Cancelled Run', status=EventStatus.CANCELLED)

        self.assertEqual(list(Event.objects.upcoming()), [sooner, later])

    def test_upcoming_uses_new_york_time_for_events_today(self):
        now = datetime.datetime(2026, 10, 19, 12, 0, tzinfo=NYC_TZ)
        morning = self.make_event(days=0, date=now.date(), time=datetime.time(9, 0))
        evening = self.make_event(days=0, date=now.date(), time=datetime.time(19, 0))

        upcoming = list(Event.objects.upcoming(now=now))
        self.assertIn(evening, upcoming)
        self.assertNotIn(morning, upcoming)

    # Feed page

    def test_feed_is_public_and_linked_from_navigation(self):
        response = self.client.get(reverse('event_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'base.html')

        landing = self.client.get(reverse('home'))
        self.assertContains(landing, f'href="{reverse("event_list")}"')

    def test_feed_shows_activity_date_time_location_and_capacity(self):
        event = self.make_event(capacity=12)
        self.make_event(activity='Morning Yoga', capacity=None)

        response = self.client.get(reverse('event_list'))

        self.assertContains(response, 'Pickup Basketball')
        self.assertContains(response, event.date.strftime('%b'))
        self.assertContains(response, '6:30 PM')
        self.assertContains(response, 'Central Park')
        self.assertContains(response, 'Manhattan')
        self.assertContains(response, 'Up to 12')
        self.assertContains(response, 'Unlimited spots')

    def test_feed_excludes_past_events_by_default_and_can_include_them(self):
        self.make_event(days=-3, activity='Old Soccer Game')
        self.make_event(activity='New Soccer Game')

        default = self.client.get(reverse('event_list'))
        self.assertContains(default, 'New Soccer Game')
        self.assertNotContains(default, 'Old Soccer Game')

        with_past = self.client.get(reverse('event_list'), {'include_past': '1'})
        self.assertContains(with_past, 'Old Soccer Game')
        self.assertContains(with_past, 'Event ended')

    def test_feed_shows_events_created_through_the_create_form(self):
        self.client.login(username='host', password=PASSWORD)
        self.client.post(reverse('event_create'), {
            'park': self.brooklyn_park.pk,
            'activity': 'Frisbee in the Park',
            'date': (self.today + datetime.timedelta(days=4)).isoformat(),
            'time': '15:00',
            'skill_level': SkillLevel.BEGINNER,
            'capacity': '',
            'description': 'Bring a disc if you have one.',
        })
        self.client.logout()

        response = self.client.get(reverse('event_list'))
        self.assertContains(response, 'Frisbee in the Park')
        self.assertContains(response, 'Prospect Park')

    def test_borough_skill_and_activity_filters_combine(self):
        self.make_event(activity='Brooklyn Beginner Soccer', park=self.brooklyn_park, skill_level=SkillLevel.BEGINNER)
        self.make_event(activity='Brooklyn Competitive Soccer', park=self.brooklyn_park,
                        skill_level=SkillLevel.COMPETITIVE)
        self.make_event(activity='Manhattan Beginner Soccer', skill_level=SkillLevel.BEGINNER)
        self.make_event(activity='Brooklyn Beginner Tennis', park=self.brooklyn_park, skill_level=SkillLevel.BEGINNER)

        response = self.client.get(reverse('event_list'), {
            'borough': Borough.BROOKLYN, 'skill': SkillLevel.BEGINNER, 'activity': 'soccer',
        })

        self.assertContains(response, 'Brooklyn Beginner Soccer')
        self.assertNotContains(response, 'Brooklyn Competitive Soccer')
        self.assertNotContains(response, 'Manhattan Beginner Soccer')
        self.assertNotContains(response, 'Brooklyn Beginner Tennis')

    def test_invalid_filter_values_are_ignored(self):
        self.make_event(activity='Any Event')
        response = self.client.get(reverse('event_list'), {'borough': 'ZZ', 'skill': 'expert'})
        self.assertContains(response, 'Any Event')

    def test_empty_state(self):
        response = self.client.get(reverse('event_list'))
        self.assertContains(response, 'No upcoming events')

    def test_feed_links_to_existing_event_detail_page(self):
        event = self.make_event()
        response = self.client.get(reverse('event_list'))
        self.assertContains(response, f'href="{event.get_absolute_url()}"')

        detail = self.client.get(event.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, event.description)
        self.assertContains(detail, 'Central Park')
        self.assertContains(detail, '10 participants')
        self.assertContains(detail, f'href="{reverse("event_list")}"')

    def test_feed_is_paginated(self):
        for i in range(25):
            self.make_event(days=1 + i, activity=f'Run {i:02d}')
        first = self.client.get(reverse('event_list'))
        self.assertEqual(len(first.context['events']), 20)
        self.assertContains(first, '25 events')
        second = self.client.get(reverse('event_list'), {'page': 2})
        self.assertEqual(len(second.context['events']), 5)

    # JSON endpoint

    def test_api_returns_upcoming_events_with_capacity_metrics(self):
        limited = self.make_event(days=1, capacity=8)
        unlimited = self.make_event(days=2, activity='Open Run', capacity=None, park=self.brooklyn_park)
        self.make_event(days=-1, activity='Past Run')

        response = self.client.get(reverse('event_list_api'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 2)
        first, second = data['results']
        self.assertEqual(first['id'], limited.pk)
        self.assertEqual(first['capacity'], 8)
        self.assertFalse(first['is_unlimited'])
        self.assertEqual(first['park']['name'], 'Central Park')
        self.assertEqual(second['id'], unlimited.pk)
        self.assertIsNone(second['capacity'])
        self.assertTrue(second['is_unlimited'])
        self.assertEqual(second['park']['borough_label'], 'Brooklyn')

    def test_api_supports_filters_and_rejects_post(self):
        self.make_event(activity='Manhattan Run')
        self.make_event(activity='Brooklyn Run', park=self.brooklyn_park)

        data = self.client.get(reverse('event_list_api'), {'borough': Borough.BROOKLYN}).json()
        self.assertEqual([e['activity'] for e in data['results']], ['Brooklyn Run'])

        self.assertEqual(self.client.post(reverse('event_list_api')).status_code, 405)

    def test_landing_page_renders_when_event_routes_are_disabled(self):
        # Production deployment-check mode serves only the landing page (config.deployment_urls).
        with self.settings(ROOT_URLCONF='config.deployment_urls'):
            response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Browse events')
        self.assertContains(response, 'href="#events"')

    def test_seed_command_creates_past_events_hidden_by_default(self):
        from django.core.management import call_command
        from io import StringIO

        call_command('seed_events', stdout=StringIO())

        default = self.client.get(reverse('event_list'))
        self.assertNotContains(default, 'Earlier Reservoir Run')
        with_past = self.client.get(reverse('event_list'), {'include_past': '1'})
        self.assertContains(with_past, 'Earlier Reservoir Run')
        self.assertContains(with_past, 'Event ended')
