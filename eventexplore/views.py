from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import Event


def _filtered_events(request):
    """Upcoming public events by default.

    Optional query parameters: ?activity=, ?borough=, ?include_past=1
    """
    if request.GET.get("include_past") == "1":
        events = Event.objects.published().order_by("start_time")
    else:
        events = Event.objects.upcoming()

    activity = request.GET.get("activity", "").strip()
    if activity in Event.ActivityType.values:
        events = events.filter(activity_type=activity)
    else:
        activity = ""

    borough = request.GET.get("borough", "").strip()
    if borough in Event.Borough.values:
        events = events.filter(borough=borough)
    else:
        borough = ""

    return events.with_capacity(), activity, borough


def _serialize(event):
    return {
        "id": event.pk,
        "title": event.title,
        "activity_type": event.activity_type,
        "activity_label": event.get_activity_type_display(),
        "location": event.location,
        "borough": event.borough,
        "borough_label": event.get_borough_display(),
        "start_time": event.start_time.isoformat(),
        "end_time": event.end_time.isoformat(),
        "capacity": event.capacity,
        "spots_taken": event.taken_count,
        "remaining_spots": event.remaining_spots,
        "is_full": event.is_full,
        "url": event.get_absolute_url(),
    }


@require_GET
def event_list(request):
    events, activity, borough = _filtered_events(request)
    return render(
        request,
        "eventexplore/event_list.html",
        {
            "events": events,
            "activity_choices": Event.ActivityType.choices,
            "borough_choices": Event.Borough.choices,
            "selected_activity": activity,
            "selected_borough": borough,
            "include_past": request.GET.get("include_past") == "1",
        },
    )


@require_GET
def event_detail(request, pk):
    event = get_object_or_404(Event.objects.published().with_capacity(), pk=pk)
    return render(request, "eventexplore/event_detail.html", {"event": event})


@require_GET
def upcoming_events_api(request):
    events, _, _ = _filtered_events(request)
    return JsonResponse({"count": len(events), "results": [_serialize(e) for e in events]})


@require_GET
def event_detail_api(request, pk):
    event = get_object_or_404(Event.objects.published().with_capacity(), pk=pk)
    data = _serialize(event)
    data["description"] = event.description
    data["is_past"] = event.is_past
    return JsonResponse(data)
