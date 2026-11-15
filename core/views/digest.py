"""
the weekly email's pages (add-weekly-email-digest): signing up, confirming and signing in.

/digest asks for an address and the shows wanted, and always shows the same "check your email"
page, so it can't be used to find out who has signed up. emails are sent after the response
has been returned (digest_tokens.send_after_response), so a known and an unknown address take
the same time. a signed-in visitor is a subscriber id in the session, re-checked on every
request; nobody is logged in as a django user.
"""

import datetime
from urllib.parse import parse_qsl

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import HttpResponseBadRequest, JsonResponse, QueryDict
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.cache import add_never_cache_headers
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .. import digest_forms, digest_mail, digest_tokens
from ..digest import ALL_AREAS, area_filter, is_stale
from ..geo_filters import COOKIE_NAME as GEO_COOKIE, parse_geo_filter
from ..location import DEVICE_LABEL, location_from_request
from ..models import Subscriber

SESSION_KEY = "subscriber_id"
SESSION_AGE = int(datetime.timedelta(days=30).total_seconds())
PENDING_KEY = "digest_pending_email"
MAX_EMAIL = 254


def guarded(view):
    """
    pages holding tokens or choices: never indexed, cached or sent to another site in a
    referrer. same-origin, not no-referrer: under no-referrer, safari sends the page's own form
    posts with "Origin: null", which django's csrf check refuses
    """

    def wrapped(request, *args, **kwargs):
        response = view(request, *args, **kwargs)
        add_never_cache_headers(response)
        response["X-Robots-Tag"] = "noindex, nofollow"
        response["Referrer-Policy"] = "same-origin"
        return response

    wrapped.__name__ = view.__name__
    return wrapped


def clean_email(text):
    """the lowercase address, or None for anything that isn't one (a line break included)"""
    text = (text or "").strip()
    if not text or len(text) > MAX_EMAIL or any(char.isspace() or ord(char) < 32 for char in text):
        return None
    try:
        validate_email(text)
    except ValidationError:
        return None
    return text.lower()


def current_subscriber(request):
    """the signed-in subscriber, loaded afresh: a deleted account ends its sessions"""
    pk = request.session.get(SESSION_KEY)
    if pk is None:
        return None
    subscriber = Subscriber.objects.filter(pk=pk, confirmed_at__isnull=False).first()
    if subscriber is None:
        request.session.pop(SESSION_KEY, None)
    return subscriber


def sign_in(request, subscriber):
    request.session.cycle_key()
    request.session[SESSION_KEY] = subscriber.pk
    request.session.set_expiry(SESSION_AGE)


def remembered_form(request):
    """the signup form, filled in from the visitor's remembered area and location"""
    cookie = request.COOKIES.get(GEO_COOKIE)
    ticked, narrowed = digest_forms.initial_from_filter(parse_geo_filter(QueryDict(cookie or "")))
    here = location_from_request(request)
    label = here.label if here and here.label != DEVICE_LABEL else ""
    return digest_forms.form_context(ticked=ticked, metro_towns_ticked=narrowed, near_label=label)


def send_later(response, subscriber, what, send_one):
    return digest_tokens.send_after_response(
        response, lambda: digest_mail.send_logged(send_one, subscriber.pk, what)
    )


@guarded
def signup(request):
    if request.method != "POST":
        return render(request, "core/digest_signup.html", remembered_form(request))
    response = redirect("digest_check_email")
    request.session[PENDING_KEY] = (request.POST.get("email") or "").strip()[:MAX_EMAIL]
    # a bot fills the hidden field; both it and a client over the limit see the normal page
    if request.POST.get("website") or digest_tokens.client_limited(request):
        return response
    address = clean_email(request.POST.get("email"))
    result = digest_forms.read_choices(request.POST)
    problems = list(result.errors)
    if address is None:
        problems.insert(0, "That doesn't look like an email address.")
    if problems or result.candidates:
        request.session.pop(PENDING_KEY, None)
        context = digest_forms.context_from_post(request.POST)
        context.update(errors=problems, candidates=result.candidates, email=(request.POST.get("email") or "")[:MAX_EMAIL])
        return render(request, "core/digest_signup.html", context)
    subscriber = Subscriber.objects.filter(email=address).first()
    if subscriber is None:
        subscriber = Subscriber.objects.create(email=address)
        digest_forms.save_choices(subscriber, result.specs)
    if digest_tokens.may_send_mail(address):
        if subscriber.confirmed:
            send_later(response, subscriber, "already-subscribed", lambda: digest_mail.send_known(subscriber))
        else:
            send_later(response, subscriber, "confirmation", lambda: digest_mail.send_confirmation(subscriber))
    return response


@guarded
def check_email(request):
    return render(request, "core/digest_check_email.html", {"email": request.session.get(PENDING_KEY, "")})


@guarded
def confirm(request, token):
    subscriber = digest_tokens.subscriber_from(token, digest_tokens.CONFIRM_SALT, digest_tokens.CONFIRM_MAX_AGE)
    if subscriber is None:
        return render(request, "core/digest_confirm.html", {"expired": True})
    if request.method == "POST":
        if subscriber.confirmed_at is None:
            Subscriber.objects.filter(pk=subscriber.pk, confirmed_at__isnull=True).update(confirmed_at=timezone.now())
        return render(request, "core/digest_confirm.html", {"done": True})
    return render(request, "core/digest_confirm.html", {"token": token})


@guarded
def sign_in_page(request):
    if current_subscriber(request):
        return redirect("digest_preferences")
    if request.method != "POST":
        return render(request, "core/digest_sign_in.html")
    address = clean_email(request.POST.get("email"))
    if address is None:
        return render(request, "core/digest_sign_in.html", {"error": "That doesn't look like an email address."})
    limited = digest_tokens.client_limited(request)
    subscriber = Subscriber.objects.filter(email=address, confirmed_at__isnull=False).first()
    code = (request.POST.get("code") or "").strip()
    if not code:
        response = render(request, "core/digest_sign_in.html", {"email": address, "sent": True})
        if subscriber and not limited and digest_tokens.may_send_mail(address):
            sent = digest_tokens.issue_code(subscriber)
            send_later(response, subscriber, "sign-in code", lambda: digest_mail.send_code(subscriber, sent))
        return response
    if subscriber and not limited and digest_tokens.check_code(subscriber, code):
        response = redirect("digest_preferences")
        sign_in(request, subscriber)
        return response
    context = {"email": address, "sent": True, "error": "That code didn't work. It may have expired or been used. Send a new one."}
    return render(request, "core/digest_sign_in.html", context)


def choice_summary(subscriber):
    """[(text, no longer listed)] for the choices on the preferences page"""
    rows = []
    for choice in subscriber.choices.select_related("venue"):
        if choice.kind == choice.Kind.AREA and choice.area_query == ALL_AREAS:
            rows.append(("All of New England", False))
        elif choice.kind == choice.Kind.AREA:
            geo_filter = area_filter(choice)
            if geo_filter:
                text = ", ".join(area.label for area in geo_filter.areas)
                rows.append((f"{text} ({', '.join(geo_filter.town_labels)})" if geo_filter.towns else text, False))
            else:
                rows.append((", ".join(value for _, value in parse_qsl(choice.area_query)) or "An area", True))
        elif choice.kind == choice.Kind.NEAR:
            rows.append((f"Within {choice.miles} miles of {choice.label}", False))
        elif choice.kind == choice.Kind.TOWN:
            rows.append((f"{choice.town}, {choice.state}", False))
        elif choice.venue:
            rows.append((choice.venue.name, False))
    return rows


def preferences_page(request, subscriber, context=None):
    context = context or digest_forms.context_from_choices(subscriber)
    context.update(subscriber=subscriber, summary=choice_summary(subscriber))
    return render(request, "core/digest_preferences.html", context)


@guarded
def preferences(request):
    subscriber = current_subscriber(request)
    if subscriber is None:
        return redirect("digest_sign_in")
    if request.method != "POST":
        return preferences_page(request, subscriber)
    action = request.POST.get("action", "save")
    if action in ("pause", "resume"):
        Subscriber.objects.filter(pk=subscriber.pk).update(paused=action == "pause")
        subscriber.refresh_from_db()
        return preferences_page(request, subscriber, None)
    result = digest_forms.read_choices(request.POST)
    if not result.ok:
        context = digest_forms.context_from_post(request.POST)
        context.update(errors=result.errors, candidates=result.candidates)
        return preferences_page(request, subscriber, context)
    digest_forms.save_choices(subscriber, result.specs)
    context = digest_forms.context_from_choices(subscriber)
    context["saved"] = True
    return preferences_page(request, subscriber, context)


@guarded
def delete_account(request):
    subscriber = current_subscriber(request)
    if subscriber is None:
        return redirect("digest_sign_in")
    if request.method == "POST":
        subscriber.delete()
        request.session.flush()
        return render(request, "core/digest_deleted.html")
    return render(request, "core/digest_delete.html", {"subscriber": subscriber})


def masked(address):
    name, _, domain = address.partition("@")
    return f"{name[:1]}***@{domain}"


@csrf_exempt
@guarded
def unsubscribe(request, token):
    """
    opening the link only shows a button; the button's post, or a mail client's one-click post
    (which has no csrf token: the signed link is the proof), pauses the email without signing in
    """
    subscriber = digest_tokens.subscriber_from(token, digest_tokens.UNSUBSCRIBE_SALT)
    if subscriber is None:
        return HttpResponseBadRequest(render(request, "core/digest_unsubscribe.html", {"bad": True}).content)
    if request.method == "POST":
        Subscriber.objects.filter(pk=subscriber.pk).update(paused=True)
        return render(request, "core/digest_unsubscribe.html", {"done": True, "address": masked(subscriber.email)})
    return render(request, "core/digest_unsubscribe.html", {"token": token, "address": masked(subscriber.email)})


@require_POST
def sign_out(request):
    request.session.flush()
    return redirect("digest_sign_in")


def suggest(request):
    """suggestions for the town and venue inputs: public venue names and towns, a few at a time"""
    text = (request.GET.get("q") or "").strip()
    found = []
    if len(text) >= 2:
        venues = digest_forms.public_venues()
        if request.GET.get("kind") == "town":
            rows = venues.filter(city_town__istartswith=text).values_list("city_town", "state").distinct()
            found = sorted({f"{town.strip()}, {state}" for town, state in rows if state})
        else:
            found = [digest_forms.venue_label(venue) for venue in venues.filter(name__icontains=text).order_by("name")]
    return JsonResponse({"suggestions": found[: digest_forms.MAX_SUGGESTIONS]})
