"""
one address for the site (openspec site-identity). when CANONICAL_HOST is set, which only
production does (stagehopper.app):

- a request on any other host (www, the service's onrender.com address) is redirected
  permanently to the same path and query at SITE_URL, except the health check;
- on the canonical host, the paths stagehopper.app served for stagehopper's landing page
  before it moved go to the same path at info.stagehopper.app.

GET and HEAD get a 301; anything else a 308, so a stale form keeps its method instead of
silently becoming a GET. the target is built from the settings, never from the Host header.
with CANONICAL_HOST empty, its default, nothing is redirected: tests, development and
preview hosts behave as before.
"""

import re

from django.conf import settings
from django.http import HttpResponsePermanentRedirect

HEALTH_PATH = "/health"
LANDING_PAGE = "https://info.stagehopper.app"
# the landing page's own files at stagehopper.app (natea/twag docs/, as it was on the move):
# its top-level pages and data, its preview images, and its city folders. the site serves
# none of these paths
LANDING_PATHS = re.compile(r"^/(?:[^/]+\.(?:html|json|geojson)|og(?:_boston|_nyc)?\.png|(?:boston|nyc)/.*)$")


class HttpResponsePermanentRedirectKeepingMethod(HttpResponsePermanentRedirect):
    status_code = 308


def redirect(request, url):
    keep_method = request.method not in ("GET", "HEAD")
    return (HttpResponsePermanentRedirectKeepingMethod if keep_method else HttpResponsePermanentRedirect)(url)


class CanonicalHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        canonical = settings.CANONICAL_HOST
        if canonical and request.path != HEALTH_PATH:
            # get_host checks the host against ALLOWED_HOSTS before anything uses it
            host = request.get_host().split(":")[0].lower()
            query = request.META.get("QUERY_STRING", "")
            suffix = request.path + (f"?{query}" if query else "")
            if host != canonical:
                return redirect(request, settings.SITE_URL + suffix)
            if LANDING_PATHS.match(request.path):
                return redirect(request, LANDING_PAGE + suffix)
        return self.get_response(request)
