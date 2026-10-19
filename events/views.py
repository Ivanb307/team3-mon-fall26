from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.views.generic import CreateView, DetailView, ListView

from parks.models import Borough

from .forms import EventCreateForm
from .models import Event, SkillLevel


def filter_events(params):
    """Apply discovery-feed filters from a GET QueryDict.

    Upcoming scheduled events by default; ?include_past=1 also shows past ones.
    Optional: ?borough=<code>, ?skill=<level>, ?activity=<text> (case-insensitive contains).
    Returns (queryset, cleaned_filters).
    """
    include_past = params.get('include_past') == '1'
    events = Event.objects.scheduled() if include_past else Event.objects.upcoming()
    events = events.select_related('park', 'organizer')

    borough = params.get('borough', '').strip()
    if borough in Borough.values:
        events = events.filter(park__borough=borough)
    else:
        borough = ''

    skill = params.get('skill', '').strip()
    if skill in SkillLevel.values:
        events = events.filter(skill_level=skill)
    else:
        skill = ''

    activity = params.get('activity', '').strip()[:100]
    if activity:
        events = events.filter(activity__icontains=activity)

    filters = {
        'borough': borough,
        'skill': skill,
        'activity': activity,
        'include_past': include_past,
    }
    return events, filters


class EventListView(ListView):
    """Public discovery feed of upcoming events (#25)."""

    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    paginate_by = 20

    def get_queryset(self):
        events, self.filters = filter_events(self.request.GET)
        return events

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            filters=self.filters,
            any_filter=any(self.filters.values()),
            borough_choices=Borough.choices,
            skill_choices=SkillLevel.choices,
        )
        return context


def serialize_event(event):
    return {
        'id': event.pk,
        'activity': event.activity,
        'skill_level': event.skill_level,
        'skill_level_label': event.get_skill_level_display(),
        'date': event.date.isoformat(),
        'time': event.time.strftime('%H:%M'),
        'starts_at': event.starts_at.isoformat(),
        'park': {
            'id': event.park_id,
            'name': event.park.name,
            'borough': event.park.borough,
            'borough_label': event.park.get_borough_display(),
        },
        'capacity': event.capacity,
        'is_unlimited': event.is_unlimited,
        'organizer': event.organizer.username,
        'url': event.get_absolute_url(),
    }


@require_GET
def upcoming_events_api(request):
    """JSON version of the discovery feed, with the same filters."""
    events, _ = filter_events(request.GET)
    results = [serialize_event(event) for event in events[:200]]
    return JsonResponse({'count': len(results), 'results': results})


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventCreateForm
    template_name = 'events/event_form.html'

    def form_valid(self, form):
        form.instance.organizer = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Event created and published!')
        return response

    def get_success_url(self):
        return reverse('event_detail', kwargs={'pk': self.object.pk})


class EventDetailView(DetailView):
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'

    def get_queryset(self):
        return Event.objects.select_related('park', 'organizer')

