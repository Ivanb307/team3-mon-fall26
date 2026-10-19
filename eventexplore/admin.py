from django.contrib import admin

from .models import Event, Registration


class RegistrationInline(admin.TabularInline):
    model = Registration
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "activity_type", "borough", "start_time", "location", "capacity", "is_published", "is_public")
    list_filter = ("borough", "activity_type", "is_published", "is_public")
    search_fields = ("title", "location", "description")
    inlines = [RegistrationInline]


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "created_at")
