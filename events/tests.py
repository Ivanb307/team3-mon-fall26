import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from parks.models import Borough, Park

from .models import CAPACITY_ERROR_MESSAGE, Event, SkillLevel

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

        self.client.login(username='organizer@nyu.edu', password=PASSWORD)
        auth_response = self.client.get(reverse('home'))
        self.assertContains(auth_response, f'href="{reverse("event_create")}"')

    def test_create_event_page_renders_active_parks_in_dropdown(self):
        self.client.login(username='organizer@nyu.edu', password=PASSWORD)
        response = self.client.get(reverse('event_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'events/event_form.html')
        self.assertContains(response, 'William McCray Playground (Manhattan)')
        self.assertNotContains(response, 'Retired Playground')

    def test_successful_event_creation_assigns_owner_and_redirects_to_event_page(self):
        self.client.login(username='organizer@nyu.edu', password=PASSWORD)
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
        self.client.login(username='organizer@nyu.edu', password=PASSWORD)
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
        self.client.login(username='organizer@nyu.edu', password=PASSWORD)
        past_date = (timezone.localdate() - datetime.timedelta(days=1)).isoformat()
        response = self.client.post(reverse('event_create'), self.valid_payload(date=past_date))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Event date and time must be in the future.')
        self.assertEqual(Event.objects.count(), 0)

    def test_blank_capacity_saves_as_unlimited_and_displays_on_event_page(self):
        self.client.login(username='organizer@nyu.edu', password=PASSWORD)
        response = self.client.post(reverse('event_create'), self.valid_payload(capacity=''), follow=True)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.first()
        self.assertIsNone(event.capacity)
        self.assertContains(response, 'Unlimited')

    def test_zero_and_negative_capacity_rejected_with_exact_error_message(self):
        self.client.login(username='organizer@nyu.edu', password=PASSWORD)
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
        self.client.login(username='organizer@nyu.edu', password=PASSWORD)
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
