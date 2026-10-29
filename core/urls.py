from django.conf import settings
from django.urls import include, path, re_path
from django.views.generic import TemplateView

from .views.autocomplete import VenueAutocomplete
from .views.calendar_feed import calendar_feed
from .views.email_subscribe import email_subscribe
from .views.event_gcal import event_gcal_redirect
from .views.event_ics_download import event_ics_download
from .views.event_redirect import event_redirect
from .views.event_submission import EventCreateView
from .views.index import index, past_month_archive
from .views.internal_db_dump import internal_db_dump
from .views.location import set_location, suggest_locations
from .views.saved_shows import saved_shows, toggle_saved_show

urlpatterns = [
    # the two main event page types:
    # - the INDEX ie the homepage ie /
    # which has 1) a "month link toolbar" aka prev/curr/next month links
    # 2) a calendar for the whole current month (i.e. if it's March 14, show March)
    # 3) a list of events which, starting ~March 2025, shows events starting today AND
    # 3 weeks of events into the future
    path("", index),
    # - the monthly archives ie /2025-02/ showing
    # all events for the entire month ie from the first to the last day of the month
    re_path(
        r"^(?P<year>\d{4})-(?P<month>\d{2})/$",
        past_month_archive,
        name="past_month_archive",
    ),
    # other urls
    path("submit-event", EventCreateView.as_view(), name="submit_event"),
    path("location", set_location, name="set_location"),
    path("location/suggest", suggest_locations, name="suggest_locations"),
    path("privacy", TemplateView.as_view(template_name="core/privacy.html"), name="privacy"),
    path("saved", saved_shows, name="saved_shows"),
    path("saved/toggle/<int:event_id>", toggle_saved_show, name="toggle_saved_show"),
    path("calendar.ics", calendar_feed, name="calendar_feed"),
    path("event/<int:event_id>/gcal", event_gcal_redirect, name="event_gcal_redirect"),
    path("event/<int:event_id>/ics", event_ics_download, name="event_ics_download"),
    path("email-subscribe", email_subscribe, name="email_subscribe"),
    path("venue-autocomplete/", VenueAutocomplete.as_view(), name="venue-autocomplete"),
    path("event/<int:event_id>", event_redirect, name="event_redirect"),
    # next url is password-protected and lets developers get a copy
    # of the prod data locally
    path("internal-api/db", internal_db_dump, name="internal_db_dump"),
]

# only dev settings define SHOW_DEBUG_TOOLBAR; the test settings (DEBUG on, for
# compilescss in ci) don't
if settings.DEBUG and getattr(settings, "SHOW_DEBUG_TOOLBAR", False):
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
