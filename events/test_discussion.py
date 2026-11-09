import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from parks.models import Borough, Park

from .models import Activity, Event, Message

User = get_user_model()


class EventDiscussionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = User.objects.create_user('discussion-host', 'discussion-host@example.test')
        cls.player = User.objects.create_user('discussion-player', 'discussion-player@example.test')
        cls.park = Park.objects.create(
            gispropnum='DISCUSS1',
            name='Discussion Park',
            borough=Borough.BROOKLYN,
            latitude=40.72,
            longitude=-73.95,
        )
        cls.event = cls.make_event('Discussion event')
        cls.other_event = cls.make_event('Other event')

    @classmethod
    def make_event(cls, title):
        return Event.objects.create(
            organizer=cls.host,
            park=cls.park,
            title=title,
            activity=Activity.BASKETBALL,
            date=timezone.localdate() + datetime.timedelta(days=1),
            time=datetime.time(18),
            description='Bring water.',
        )

    def make_message(self, body, *, event=None, author=None, is_announcement=False, created_at=None):
        message = Message.objects.create(
            event=event or self.event,
            author=author or self.player,
            body=body,
            is_announcement=is_announcement,
        )
        if created_at:
            Message.objects.filter(pk=message.pk).update(created_at=created_at)
        return message

    def test_announcements_come_first_newest_first_then_messages_oldest_first(self):
        base_time = timezone.now()
        self.make_message(
            'Old announcement',
            author=self.host,
            is_announcement=True,
            created_at=base_time - datetime.timedelta(days=3),
        )
        self.make_message(
            'New announcement',
            author=self.host,
            is_announcement=True,
            created_at=base_time - datetime.timedelta(days=1),
        )
        self.make_message('Old question', created_at=base_time - datetime.timedelta(hours=3))
        self.make_message('New question', created_at=base_time - datetime.timedelta(hours=1))
        self.make_message(
            'Participant announcement flag',
            is_announcement=True,
            created_at=base_time - datetime.timedelta(hours=2),
        )

        response = self.client.get(self.event.get_absolute_url())
        content = response.content.decode()

        self.assertLess(content.index('New announcement'), content.index('Old announcement'))
        self.assertLess(content.index('Old announcement'), content.index('Old question'))
        self.assertLess(content.index('Old question'), content.index('Participant announcement flag'))
        self.assertLess(content.index('Participant announcement flag'), content.index('New question'))
        self.assertContains(response, reverse('public_profile', kwargs={'username': self.host.username}))
        self.assertContains(response, reverse('public_profile', kwargs={'username': self.player.username}))
        self.assertContains(response, '<time datetime=', html=False)

    def test_discussion_is_scoped_to_the_current_event(self):
        self.make_message('Visible here')
        self.make_message('Only on the other event', event=self.other_event)

        response = self.client.get(self.event.get_absolute_url())

        self.assertContains(response, 'Visible here')
        self.assertNotContains(response, 'Only on the other event')

    def test_empty_discussion_shows_prompt(self):
        response = self.client.get(self.event.get_absolute_url())

        self.assertContains(response, 'No messages yet. Ask a question below!')

    def test_message_body_is_html_escaped(self):
        self.make_message('<script>alert("unsafe")</script>')

        response = self.client.get(self.event.get_absolute_url())

        self.assertContains(response, '&lt;script&gt;alert(&quot;unsafe&quot;)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert("unsafe")</script>')
