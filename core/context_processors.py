from django.conf import settings


def analytics(request):
    """the analytics accounts set in .env; base.html loads each tracker only when its id is set"""
    return {
        "google_analytics_id": settings.GOOGLE_ANALYTICS_ID,
        "goatcounter_code": settings.GOATCOUNTER_CODE,
    }


def contact(request):
    return {"contact_email": settings.CONTACT_EMAIL}
