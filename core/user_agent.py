"""
the user agent the site's api clients send (musicbrainz, wikidata, last.fm, the census
downloads): who we are and how to reach us, in the form musicbrainz asks for,
"AppName/version ( contact )", so a service can get in touch before it blocks us.

the email is API_CONTACT_EMAIL, set in .env and on render; without it the user agent
gives only the site's address.
"""

import os

SITE = "https://newenglandmusic.onrender.com"


def user_agent():
    """read on each request, so a changed API_CONTACT_EMAIL takes effect without a restart of the code"""
    email = os.environ.get("API_CONTACT_EMAIL", "").strip()
    contact = f"{SITE}; {email}" if email else SITE
    return f"venue-db-event-check/1.0 ( {contact} )"
