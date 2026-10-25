from core.utils_aws import aws_mail_sender
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        aws_mail_sender.send_email(
            settings.DEFAULT_FROM_EMAIL,
            settings.CONTACT_EMAIL,
            "this is the subject",
            "this is the content",
            "and this is the html version",
        )
