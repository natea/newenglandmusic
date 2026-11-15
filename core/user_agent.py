"""
the user agent the site's api clients send (musicbrainz, wikidata, last.fm, the census
downloads): who we are and how to reach us, in the form musicbrainz asks for,
"AppName/version ( contact )", so a service can get in touch before it blocks us.

the address is SITE_URL, which the scheduled jobs get from the web service (render.yaml),
and the email is API_CONTACT_EMAIL, set in .env and on render; without it the user agent
gives only the site's address.
"""

import os

from django.conf import settings


def user_agent():
    """read on each request, so a changed API_CONTACT_EMAIL takes effect without a restart of the code"""
    site = settings.SITE_URL
    email = os.environ.get("API_CONTACT_EMAIL", "").strip()
    contact = f"{site}; {email}" if email else site
    return f"venue-db-event-check/1.0 ( {contact} )"
