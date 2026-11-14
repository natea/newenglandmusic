from django.conf import settings


def analytics(request):
    """the analytics accounts set in .env; base.html loads each tracker only when its id is set"""
    return {
        "google_analytics_id": settings.GOOGLE_ANALYTICS_ID,
        "goatcounter_code": settings.GOATCOUNTER_CODE,
        "posthog_project_token": settings.POSTHOG_PROJECT_TOKEN,
        "posthog_host": settings.POSTHOG_HOST,
    }


def maps(request):
    return {
        "protomaps_api_key": settings.PROTOMAPS_API_KEY,
        # written as js literals here, so a localized template can't render "43,2"
        "map_center": f"[{settings.MAP_CENTER_LONGITUDE}, {settings.MAP_CENTER_LATITUDE}]",
        "map_zoom": f"{settings.MAP_ZOOM}",
    }


def site(request):
    """the site's name and tagline from .env (SITE_NAME, SITE_TAGLINE), for text that names the site"""
    return {"site_name": settings.SITE_NAME, "site_tagline": settings.SITE_TAGLINE.strip()}


def contact(request):
    return {"contact_email": settings.CONTACT_EMAIL}
