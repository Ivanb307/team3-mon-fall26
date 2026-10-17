from django.urls import path

from .views import EventCreateView, EventDetailView

urlpatterns = [
    path('events/create/', EventCreateView.as_view(), name='event_create'),
    path('events/<int:pk>/', EventDetailView.as_view(), name='event_detail'),
]

