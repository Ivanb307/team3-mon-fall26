"""Only public diagnostics for the temporary HTTP deployment check."""
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("health/", views.health, name="health"),
    path("ready/", views.ready, name="ready"),
]
