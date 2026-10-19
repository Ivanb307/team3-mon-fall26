from django.urls import path

from . import views

app_name = "eventexplore"

urlpatterns = [
    path("", views.event_list, name="list"),
    path("<int:pk>/", views.event_detail, name="detail"),
    path("api/upcoming/", views.upcoming_events_api, name="api_upcoming"),
    path("api/<int:pk>/", views.event_detail_api, name="api_detail"),
]
