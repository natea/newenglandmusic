"""
the sites framework's record (django.contrib.sites) kept in step with SITE_URL and SITE_NAME
after every migrate (CoreConfig.ready), so anything that asks django for the current site
(password-reset emails, the sitemap framework, django-meta) gets this site's own address
rather than the example.com every new database starts with.

the settings are the one source: render's address comes from RENDER_EXTERNAL_URL, a custom
domain from SITE_URL, and the next deploy updates the record. the admin shows it read-only.
"""

from urllib.parse import urlsplit

from django.conf import settings


def site_domain():
    """"newenglandmusic.onrender.com" from SITE_URL, port kept ("localhost:8001")"""
    return urlsplit(settings.SITE_URL).netloc or settings.SITE_URL


def sync_site_record(**kwargs):
    from django.contrib.sites.models import Site

    Site.objects.update_or_create(pk=settings.SITE_ID, defaults={"domain": site_domain(), "name": settings.SITE_NAME})
    # get_current_site caches the record per process
    Site.objects.clear_cache()
