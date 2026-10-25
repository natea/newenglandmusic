from django.conf import settings


def analytics(request):
    """the analytics accounts set in .env; base.html loads each tracker only when its id is set"""
    return {
        "google_analytics_id": settings.GOOGLE_ANALYTICS_ID,
        "goatcounter_code": settings.GOATCOUNTER_CODE,
    }


def maps(request):
    return {
        "protomaps_api_key": settings.PROTOMAPS_API_KEY,
        # written as js literals here, so a localized template can't render "43,2"
        "map_center": f"[{settings.MAP_CENTER_LONGITUDE}, {settings.MAP_CENTER_LATITUDE}]",
        "map_zoom": f"{settings.MAP_ZOOM}",
    }


def contact(request):
    return {"contact_email": settings.CONTACT_EMAIL}
