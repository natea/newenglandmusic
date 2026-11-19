import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from core import preview_data


class Command(BaseCommand):
    help = (
        "removes people's data from a copy of the live database, before it is loaded where pull "
        "request previews are (preview-environments). never runs against the live database."
    )

    def handle(self, *args, **options):
        refusal = preview_data.refusal(os.environ.get("DJANGO_SETTINGS_MODULE", ""), settings.DATABASES["default"].get("HOST"))
        if refusal:
            raise CommandError(refusal)
        missing = preview_data.unclassified(connection.introspection.table_names())
        if missing:
            raise CommandError("these tables are on no list in core/preview_data.py: " + ", ".join(missing))
        with transaction.atomic():
            for what, rows in preview_data.scrub(connection):
                self.stdout.write(f"{what}: {rows} rows")
