"""
signed links, sign-in codes and sending limits for the weekly email (add-weekly-email-digest).

    token = confirm_token(subscriber)        # a link in the confirmation email, lasts 7 days
    subscriber = subscriber_from(token, CONFIRM_SALT, max_age=CONFIRM_MAX_AGE)
    code = issue_code(subscriber)            # six digits, emailed; only a keyed hash is stored
    check_code(subscriber, code)             # works once, for 15 minutes

everything reads the time from django.utils.timezone.now so tests can fix it. the limits count
rows of MailRequest (an address or a hash of the client's address, and a time), which the
weekly command deletes after a day.
"""

import datetime
import hashlib
import hmac
import secrets

from django.conf import settings
from django.core import signing
from django.db.models import F
from django.utils import timezone

from core.models import MailRequest, SignInCode, Subscriber

CONFIRM_SALT = "digest-confirm"
UNSUBSCRIBE_SALT = "digest-unsubscribe"
CONFIRM_MAX_AGE = datetime.timedelta(days=7)
CODE_MAX_AGE = datetime.timedelta(minutes=15)
CODE_TRIES = 5
ADDRESS_WRONG_TRIES_PER_HOUR = 10
MAILS_PER_ADDRESS_PER_HOUR = 3
REQUESTS_PER_CLIENT_PER_HOUR = 10
HOUR = datetime.timedelta(hours=1)

MAIL = "mail"
REQUEST = "request"
WRONG_CODE = "wrong-code"


def sign(subscriber, salt):
    stamp = int(timezone.now().timestamp())
    return signing.Signer(salt=salt).sign(f"{subscriber.pk}:{stamp}")


def subscriber_from(token, salt, max_age=None):
    """the Subscriber a signed link names, or None when it was altered, has expired or is gone"""
    try:
        value = signing.Signer(salt=salt).unsign(token or "")
        pk, stamp = value.split(":")
        signed_at = datetime.datetime.fromtimestamp(int(stamp), datetime.timezone.utc)
        if max_age is not None and timezone.now() - signed_at > max_age:
            return None
        return Subscriber.objects.filter(pk=int(pk)).first()
    except (signing.BadSignature, ValueError):
        return None


def confirm_token(subscriber):
    return sign(subscriber, CONFIRM_SALT)


def unsubscribe_token(subscriber):
    # never expires: an old email must still work
    return sign(subscriber, UNSUBSCRIBE_SALT)


def keyed_hash(purpose, value):
    # keyed, so a leaked table can't be reversed by trying every code or address
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, f"{purpose}:{value}".encode(), hashlib.sha256).hexdigest()


def code_hash(subscriber, code):
    return keyed_hash("digest-code", f"{subscriber.pk}:{code}")


def issue_code(subscriber):
    """a new six-digit code, cancelling the earlier ones"""
    SignInCode.objects.filter(subscriber=subscriber, used_at__isnull=True).update(used_at=timezone.now())
    code = f"{secrets.randbelow(10**6):06d}"
    SignInCode.objects.create(subscriber=subscriber, code_hash=code_hash(subscriber, code))
    return code


def record(kind, address="", client_hash=""):
    # the time is set here, not by the field's default, which can't be patched in tests
    return MailRequest.objects.create(kind=kind, address=address, client_hash=client_hash, created_at=timezone.now())


def address_locked(address):
    since = timezone.now() - HOUR
    wrong = MailRequest.objects.filter(kind=WRONG_CODE, address=address.lower(), created_at__gte=since)
    return wrong.count() >= ADDRESS_WRONG_TRIES_PER_HOUR


def check_code(subscriber, code):
    """True when code is the subscriber's newest, unused, unexpired code and tries remain"""
    if address_locked(subscriber.email):
        return False
    newest = SignInCode.objects.filter(
        subscriber=subscriber, used_at__isnull=True, created_at__gte=timezone.now() - CODE_MAX_AGE
    ).order_by("-created_at", "-pk").first()
    if newest is None:
        return False
    # count the try first, so parallel guesses can't get more than CODE_TRIES
    counted = SignInCode.objects.filter(pk=newest.pk, used_at__isnull=True, attempts__lt=CODE_TRIES)
    if not counted.update(attempts=F("attempts") + 1):
        return False
    right = hmac.compare_digest(newest.code_hash, code_hash(subscriber, (code or "").strip()))
    if right:
        # single use: only one of two parallel correct entries gets the row
        return bool(SignInCode.objects.filter(pk=newest.pk, used_at__isnull=True).update(used_at=timezone.now()))
    record(WRONG_CODE, address=subscriber.email)
    return False


def may_send_mail(address):
    """records a confirmation, already-subscribed or code email to address; False over the limit"""
    address = address.lower()
    recent = MailRequest.objects.filter(kind=MAIL, address=address, created_at__gte=timezone.now() - HOUR)
    if recent.count() >= MAILS_PER_ADDRESS_PER_HOUR:
        return False
    record(MAIL, address=address)
    return True


def client_address(request):
    """
    the client's address as the host saw it: the last X-Forwarded-For entry, which the host
    appends and a visitor can't set (the leftmost entries can be forged)
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    last = forwarded.split(",")[-1].strip()
    return last or request.META.get("REMOTE_ADDR", "")


def client_hash(request):
    return keyed_hash("digest-client", client_address(request))


def client_limited(request):
    """records a signup or sign-in request from this client; True when it is over the limit"""
    hashed = client_hash(request)
    recent = MailRequest.objects.filter(kind=REQUEST, client_hash=hashed, created_at__gte=timezone.now() - HOUR)
    if recent.count() >= REQUESTS_PER_CLIENT_PER_HOUR:
        return True
    record(REQUEST, client_hash=hashed)
    return False


def delete_old_requests():
    return MailRequest.objects.filter(created_at__lt=timezone.now() - datetime.timedelta(days=1)).delete()[0]


def send_after_response(response, send):
    """
    runs send() once the response has been returned (django closes a response after the
    server has written it), so a known and an unknown address take the same time
    """
    response._resource_closers.append(send)
    return response
