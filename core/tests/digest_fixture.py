"""
a fake Amazon SES and the settings the weekly email needs, for tests that send mail: nothing
reaches the network. the fake records each raw message; set `error` to make it raise.
"""

import datetime
import email
import re
from email import policy
from unittest import mock

from django.test import TestCase, override_settings

from core.tests.census_fixture import census_places
from core.tests.geo_fixture import load_geo_fixture
from core.utils_aws import SesMailSender

SITE = "https://digest.example.org"


class FakeSes:
    def __init__(self):
        self.error = None
        self.sent = []

    def send_raw_email(self, **kwargs):
        if self.error:
            raise self.error
        self.sent.append(kwargs)
        return {"MessageId": f"id-{len(self.sent)}"}


def parse(call):
    return email.message_from_bytes(call["RawMessage"]["Data"], policy=policy.default)


def body(message, kind="plain"):
    return message.get_body((kind,)).get_content()


class DigestTestCase(TestCase):
    """geo areas, census places, a fake SES and a sender and site address that may send"""

    def setUp(self):
        load_geo_fixture()
        census_places()
        self.ses = FakeSes()
        for patcher in (
            mock.patch("core.utils_aws.aws_mail_sender", SesMailSender(self.ses)),
            override_settings(DEFAULT_FROM_EMAIL="events@digest.example.org", SITE_URL=SITE),
        ):
            patcher.start() if hasattr(patcher, "start") else patcher.enable()
            self.addCleanup(patcher.stop if hasattr(patcher, "stop") else patcher.disable)

    def messages(self):
        return [parse(call) for call in self.ses.sent]

    def links(self, message):
        return re.findall(re.escape(SITE) + r"/[^\s\"<>]+", body(message))
