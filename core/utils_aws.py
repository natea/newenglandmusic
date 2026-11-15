import logging
from email.message import EmailMessage

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

"""
boto3 will fetch these env vars:
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
ie no need to expose them via django.conf
"""


class SesMailSender:
    """Encapsulates functions to send emails with Amazon SES."""

    def __init__(self, ses_client):
        """
        :param ses_client: A Boto3 Amazon SES client.
        """
        self.ses_client = ses_client

    def send_email(self, source, destination, subject, text, html, reply_tos=None):
        """
        Sends an email.

        Note: If your account is in the Amazon SES  sandbox, the source and
        destination email accounts must both be verified.

        :param source: The source email account.
        :param destination: The destination email account.
        :param subject: The subject of the email.
        :param text: The plain text version of the body of the email.
        :param html: The HTML version of the body of the email.
        :param reply_tos: Email accounts that will receive a reply if the recipient
                          replies to the message.
        :return: The ID of the message, assigned by Amazon SES.
        """
        send_args = {
            "Source": source,
            "Destination": {"ToAddresses": [destination]},
            "Message": {
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": text}, "Html": {"Data": html}},
            },
        }
        if reply_tos is not None:
            send_args["ReplyToAddresses"] = reply_tos
        try:
            response = self.ses_client.send_email(**send_args)
            message_id = response["MessageId"]
            logger.info("Sent mail %s from %s to %s.", message_id, source, destination)
        except ClientError as e:
            logger.exception(
                "ERROR Couldn't send mail from %s to %s.", source, destination
            )
        else:
            return message_id

    def send_raw_email(self, source, destination, subject, text, html, headers=None):
        """
        Sends a text and HTML email as a raw MIME message, so it can carry extra headers
        (List-Unsubscribe). Unlike send_email(), failures raise (ClientError for a rejection
        or a throttling reply, BotoCoreError for missing credentials), so the caller decides.
        EmailMessage refuses line breaks in headers, so an address can't inject one.

        :param headers: extra header names and values, such as List-Unsubscribe.
        :return: The ID of the message, assigned by Amazon SES.
        """
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = source
        message["To"] = destination
        for name, value in (headers or {}).items():
            message[name] = value
        message.set_content(text)
        message.add_alternative(html, subtype="html")
        response = self.ses_client.send_raw_email(
            Source=source,
            Destinations=[destination],
            RawMessage={"Data": message.as_bytes()},
        )
        message_id = response["MessageId"]
        logger.info("Sent raw mail %s.", message_id)
        return message_id


# we are in us-east-2 for some reason
aws_mail_sender = SesMailSender(boto3.client("ses", region_name="us-east-2"))
