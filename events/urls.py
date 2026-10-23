from django.urls import path

from .views import EventCreateView, EventDetailView, EventListView, upcoming_events_api

urlpatterns = [
    path('events/', EventListView.as_view(), name='event_list'),
    path('events/api/upcoming/', upcoming_events_api, name='event_list_api'),
    path('events/create/', EventCreateView.as_view(), name='event_create'),
    path('events/<int:pk>/', EventDetailView.as_view(), name='event_detail'),
]
