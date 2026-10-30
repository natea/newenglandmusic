from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.db.models.functions import TruncMonth

from .models import Artist, Band, Event, StaticPage
from .utils_datemath import beginning_of_day, get_current_new_york_datetime


class SiteSitemap(Sitemap):
    def items(self):
        url_list = ["/"]

        # all public static pages
        for static_page in StaticPage.objects.all():
            url_list.append(static_page.get_absolute_url())

        # all approved events, extracting the year-month only,
        # and getting a unique list of that
        for event_year_month in set(
            Event.objects.annotate(m=TruncMonth("starttime")).values_list(
                "m", flat=True
            )
        ):
            url_list.append(f"/{event_year_month.year}-{event_year_month.month:02d}/")

        # band and artist pages with an upcoming approved show; the rest are noindex
        today = beginning_of_day(get_current_new_york_datetime())
        for model, field in ((Band, "band"), (Artist, "artist")):
            acts = model.objects.filter(
                performances__event__is_approved=True, performances__event__starttime__gte=today
            ).distinct()
            url_list.extend(act.get_absolute_url() for act in acts)

        # uniquify.
        return list(set(url_list))

    # locations gets items which are supposed to be objects, and you're supposed
    # to call get_absolute_url on those... but if you already deal with urls, you don't
    # need to do that.
    def location(self, item):
        return item

    # use the site's own address (SITE_URL) rather than the sites framework's record,
    # which still says example.com
    def get_domain(self, site=None):
        return settings.META_SITE_DOMAIN

    def get_protocol(self, protocol=None):
        return settings.META_SITE_PROTOCOL
