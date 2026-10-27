"""
runs the tests without the developer's api keys from .env, as ci runs them: tests mock
every service, and a key left set would send a test to the real one (a set
GOOGLE_SERVICE_ACCOUNT_JSON reads the sheet with the sheets api instead of the mocked gog).
"""

import os

from django.test.runner import DiscoverRunner

KEYS = (
    "ANTHROPIC_API_KEY",
    "TICKETMASTER_API_KEY",
    "EVENTBRITE_API_KEY",
    "GOOGLE_PLACES_API_KEY",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "SPOTIFY_CLIENT_ID",
    "SPOTIFY_CLIENT_SECRET",
)


class TestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        for key in KEYS:
            os.environ.pop(key, None)
        super().setup_test_environment(**kwargs)
