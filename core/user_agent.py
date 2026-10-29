"""
the user agent the site's api clients send (musicbrainz, wikidata, last.fm, the census
downloads): who we are and how to reach us, in the form musicbrainz asks for,
"AppName/version ( contact )", so a service can get in touch before it blocks us.
"""

CONTACT_EMAIL = "newenglandmusic843@gmail.com"
SITE = "https://newenglandmusic.onrender.com"
USER_AGENT = f"venue-db-event-check/1.0 ( {SITE}; {CONTACT_EMAIL} )"
