"""
a venue the public site lists, for tests whose events only need to appear (it hides events at venues
outside New England, or with none):

    Event.objects.create(title="a show", starttime=soon, venue=new_england_venue())
"""

from core.models import Venue


def new_england_venue():
    venue, _ = Venue.objects.get_or_create(
        sheet_id="NE-TEST", defaults={"name": "Test venue", "city_town": "Boston", "state": "MA"}
    )
    return venue
