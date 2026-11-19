import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.core.management.base import BaseCommand, CommandError

from core import preview_data


class Command(BaseCommand):
    help = (
        "makes the one account a pull request's preview has, preview-admin, from the password "
        "hash in PREVIEW_ADMIN_PASSWORD_HASH (preview-environments). the password itself is never given."
    )

    def handle(self, *args, **options):
        refusal = preview_data.refusal(os.environ.get("DJANGO_SETTINGS_MODULE", ""), settings.DATABASES["default"].get("HOST"))
        if refusal:
            raise CommandError(refusal)
        self.stdout.write(set_admin(os.environ.get("PREVIEW_ADMIN_PASSWORD_HASH", "")))


def set_admin(password_hash):
    """creates or updates preview-admin with the hashed password, and removes every other account"""
    try:
        identify_hasher(password_hash)
    except ValueError:
        raise CommandError("PREVIEW_ADMIN_PASSWORD_HASH isn't a Django password hash")
    User = get_user_model()
    others = User.objects.exclude(username=preview_data.PREVIEW_ADMIN).delete()[0]
    User.objects.update_or_create(
        username=preview_data.PREVIEW_ADMIN,
        defaults={"password": password_hash, "is_staff": True, "is_superuser": True, "is_active": True, "email": ""},
    )
    return f"{preview_data.PREVIEW_ADMIN} is set" + (f"; removed {others} other account rows" if others else "")
