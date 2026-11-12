from django.http import HttpResponse


def health(request):
    """render's health check: answers without touching the database, at any host (see core/middleware.py)"""
    return HttpResponse("ok", content_type="text/plain")
