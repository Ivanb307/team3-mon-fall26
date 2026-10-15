"""Temporary deployment page and infrastructure probes."""
from django.db import DatabaseError, connection
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_safe


@require_safe
def home(request):
    return HttpResponse(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>NYC Active</title><h1>NYC Active is running</h1>'
        '<p>The team Django project is deployed on AWS.</p>'
        '<p>This temporary page will be replaced by the team frontend.</p></html>'
    )


@require_safe
def health(request):
    return JsonResponse({"status": "ok"})


@require_safe
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
