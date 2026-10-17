from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('activity', 'park', 'organizer', 'date', 'time', 'skill_level', 'capacity', 'status')
    list_filter = ('status', 'skill_level', 'date')
    search_fields = ('activity', 'description', 'park__name', 'organizer__username')
    raw_id_fields = ('park', 'organizer')

