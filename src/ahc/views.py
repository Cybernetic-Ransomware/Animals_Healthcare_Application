"""Project-level operational views (health probes)."""

from django.db import DatabaseError, connection
from django.http import HttpRequest, JsonResponse


def livez(request: HttpRequest) -> JsonResponse:
    """Liveness probe: the process is up. No external dependencies."""
    return JsonResponse({"status": "ok"})


def readyz(request: HttpRequest) -> JsonResponse:
    """Readiness probe: the app can serve traffic (database reachable)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
