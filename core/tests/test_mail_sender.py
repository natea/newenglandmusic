import email
from email import policy
from unittest import mock

from botocore.exceptions import ClientError, NoCredentialsError
from django.test import SimpleTestCase

from core.utils_aws import SesMailSender


class FakeSes:
    """records what it is given; raises what it is told to"""

    def __init__(self, error=None):
        self.error = error
        self.raw = []
        self.simple = []

    def send_raw_email(self, **kwargs):
        if self.error:
            raise self.error
        self.raw.append(kwargs)
        return {"MessageId": "raw-1"}

    def send_email(self, **kwargs):
        if self.error:
            raise self.error
        self.simple.append(kwargs)
        return {"MessageId": "simple-1"}


def parsed(call):
    return email.message_from_bytes(call["RawMessage"]["Data"], policy=policy.default)


class RawEmailTestCase(SimpleTestCase):
    def test_both_parts_and_headers_are_in_the_message(self):
        ses = FakeSes()
        message_id = SesMailSender(ses).send_raw_email(
            "from@example.org", "to@example.com", "Hello", "plain body", "<p>html body</p>",
            headers={"List-Unsubscribe": "<https://example.org/u>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"},
        )
        self.assertEqual(message_id, "raw-1")
        call = ses.raw[0]
        self.assertEqual(call["Destinations"], ["to@example.com"])
        message = parsed(call)
        self.assertEqual(message["Subject"], "Hello")
        self.assertEqual(message["List-Unsubscribe"], "<https://example.org/u>")
        self.assertEqual(message["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click")
        self.assertEqual(message.get_content_type(), "multipart/alternative")
        self.assertIn("plain body", message.get_body(("plain",)).get_content())
        self.assertIn("<p>html body</p>", message.get_body(("html",)).get_content())

    def test_a_client_error_a_credentials_error_and_a_throttle_are_raised(self):
        errors = [
            ClientError({"Error": {"Code": "MessageRejected", "Message": "no"}}, "SendRawEmail"),
            NoCredentialsError(),
            ClientError({"Error": {"Code": "Throttling", "Message": "slow down"}}, "SendRawEmail"),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__), self.assertRaises(type(error)):
                SesMailSender(FakeSes(error)).send_raw_email("from@example.org", "to@example.com", "s", "t", "<p>h</p>")

    def test_a_line_break_in_an_address_is_refused(self):
        ses = FakeSes()
        with self.assertRaises(ValueError):
            SesMailSender(ses).send_raw_email("from@example.org", "to@example.com\nBcc: x@example.com", "s", "t", "<p>h</p>")
        self.assertEqual(ses.raw, [])

    def test_send_email_still_behaves_as_before(self):
        ses = FakeSes()
        self.assertEqual(SesMailSender(ses).send_email("a@example.org", "b@example.com", "s", "t", "<p>h</p>"), "simple-1")
        self.assertEqual(ses.simple[0]["Destination"], {"ToAddresses": ["b@example.com"]})
        error = ClientError({"Error": {"Code": "MessageRejected", "Message": "no"}}, "SendEmail")
        with mock.patch("core.utils_aws.logger"):
            self.assertIsNone(SesMailSender(FakeSes(error)).send_email("a@example.org", "b@example.com", "s", "t", "<p>h</p>"))
