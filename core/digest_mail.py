"""
the emails of the weekly email feature: the confirmation, the already-subscribed notice and the
sign-in code, and the sender checks the weekly email shares (add-weekly-email-digest).

    send_confirmation(subscriber)

every one is sent as a raw multipart text and HTML message through core.utils_aws, which is
looked up when sending so tests can swap in a fake. nothing is sent from the placeholder sender
or while the site address would make every link dead; failures raise, and the views that send
after the response was returned log them without the address.
"""

import logging
from html import escape
from urllib.parse import urlparse

from django.conf import settings
from django.urls import reverse

from core import digest_tokens, utils_aws

logger = logging.getLogger(__name__)

PLACEHOLDER_SENDER = "webmaster@localhost"
CONFIRM_SUBJECT = "Confirm your weekly email"
KNOWN_SUBJECT = "You already get the weekly email"
CODE_SUBJECT = "Your sign-in code"


class MailNotReady(Exception):
    """the sender or the site address isn't set up, so nothing may be sent"""


def check_ready():
    """the sender address, raising MailNotReady when mail would go out wrong"""
    sender = settings.DEFAULT_FROM_EMAIL
    if not sender or sender == PLACEHOLDER_SENDER:
        raise MailNotReady("DEFAULT_FROM_EMAIL is not set to a verified sender")
    site = urlparse(settings.SITE_URL or "")
    if site.scheme != "https" or not site.hostname or site.hostname in ("localhost", "127.0.0.1", "::1"):
        raise MailNotReady("SITE_URL is not an https address, so the links in the email would be dead")
    return sender


def site_url(path):
    return settings.SITE_URL.rstrip("/") + path


def send(address, subject, text, html, headers=None):
    return utils_aws.aws_mail_sender.send_raw_email(check_ready(), address, subject, text, html, headers=headers)


def paragraphs(*lines):
    """the same lines as plain text and as HTML paragraphs, with links left as text for the HTML to link"""
    text = "\n\n".join(lines) + "\n"
    html = "".join(f"<p>{escape(line)}</p>" for line in lines)
    return text, html


def link_html(url):
    return f'<p><a href="{escape(url)}">{escape(url)}</a></p>'


def send_confirmation(subscriber):
    url = site_url(reverse("digest_confirm", args=[digest_tokens.confirm_token(subscriber)]))
    intro = [
        f"Someone asked for {settings.SITE_NAME}'s weekly email of upcoming shows at this address. If it was you, follow this link and press Confirm. It works for 7 days:"
    ]
    outro = ["If it wasn't you, ignore this email and nothing will be sent."]
    text, html = paragraphs(*intro)
    text += f"\n{url}\n\n" + outro[0] + "\n"
    html += link_html(url) + paragraphs(*outro)[1]
    return send(subscriber.email, CONFIRM_SUBJECT, text, html)


def send_known(subscriber):
    url = site_url(reverse("digest_sign_in"))
    lines = [f"Someone asked to sign up this address for {settings.SITE_NAME}'s weekly email, but it already has a subscription."]
    text, html = paragraphs(*lines)
    follow = "To change your shows or stop the email, ask for a sign-in code here:"
    text += f"\n{follow}\n\n{url}\n\nIf it wasn't you, ignore this email.\n"
    html += f"<p>{escape(follow)}</p>" + link_html(url) + "<p>If it wasn't you, ignore this email.</p>"
    return send(subscriber.email, KNOWN_SUBJECT, text, html)


def send_code(subscriber, code):
    lines = [f"Your {settings.SITE_NAME} sign-in code is {code}.", "It works once and expires in 15 minutes. If you didn't ask for it, ignore this email."]
    text, html = paragraphs(*lines)
    return send(subscriber.email, CODE_SUBJECT, text, html)


def send_logged(send_one, subscriber_id, what):
    """runs send_one(), logging a failure by subscriber id (never the address) instead of raising"""
    try:
        send_one()
    except Exception as error:
        # the class name only: a message or traceback could hold the address
        logger.error("couldn't send the %s email to subscriber %s: %s", what, subscriber_id, type(error).__name__)
