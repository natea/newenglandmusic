from django.core.management.base import BaseCommand, CommandError

from core.job_runs import RecordedCommand
from core.models import Artist, Band

"""
marks bands and artists inactive, so the Bands & artists index leaves them off (their pages
and show links stay). an act is named by its page address: its slug, or bands/slug or
artists/slug to name the kind, since a slug is unique only within a kind.

run as:

python manage.py mark_inactive_acts [--file addresses.txt] [--dry-run] [--active] [slug ...]

a bare slug matching both a band and an artist marks neither and is reported as ambiguous;
an address matching nothing is reported as not found. the file has one address a line, and
blank lines and lines starting with # are ignored. --active reverses the mark. it is run by
hand, not scheduled; imports and enrichment never write the mark, so they can't undo it.
"""

KINDS = {"bands": Band, "artists": Artist}


def addresses_in(path):
    """the addresses in a file, one a line, without blank lines and # comments"""
    try:
        with open(path, encoding="utf-8") as file:
            lines = [line.strip() for line in file]
    except OSError as error:
        raise CommandError(f"can't read {path}: {error}")
    return [line for line in lines if line and not line.startswith("#")]


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("addresses", nargs="*", help="slugs, or bands/slug or artists/slug")
        parser.add_argument("--file", help="a file of addresses, one a line")
        parser.add_argument("--active", action="store_true", help="mark the acts active again")
        parser.add_argument("--dry-run", action="store_true", help="say what would change, but change nothing")

    def handle(self, *args, **options):
        addresses = [*options["addresses"], *(addresses_in(options["file"]) if options["file"] else [])]
        if not addresses:
            raise CommandError("give at least one address, or --file")
        inactive = not options["active"]
        found, ambiguous, missing = self.resolve(addresses)

        verb = "would mark" if options["dry_run"] else "marked"
        state = "inactive" if inactive else "active"
        changed = 0
        for act in found:
            if act.is_inactive == inactive:
                continue
            changed += 1
            self.stdout.write(f"{verb} {state}: {act.name} ({act.get_absolute_url()})")
            if not options["dry_run"]:
                # update(), so the act's events aren't re-rendered
                type(act).objects.filter(pk=act.pk).update(is_inactive=inactive)
        for address in ambiguous:
            self.stdout.write(self.style.WARNING(f"ambiguous, a band and an artist (use bands/ or artists/): {address}"))
        for address in missing:
            self.stdout.write(self.style.WARNING(f"not found: {address}"))
        self.stdout.write(f"{changed} {'would be ' if options['dry_run'] else ''}changed, {len(found) - changed} already {state}")
        self.job_summary = [("changed", 0 if options["dry_run"] else changed)]

    def resolve(self, addresses):
        """the acts the addresses name, plus the addresses that were ambiguous or matched nothing"""
        found, ambiguous, missing = [], [], []
        for address in addresses:
            matches = self.matches(address)
            if len(matches) > 1:
                ambiguous.append(address)
            elif matches:
                found.append(matches[0])
            else:
                missing.append(address)
        return found, ambiguous, missing

    def matches(self, address):
        """the acts at an address, from either kind, or the named kind"""
        kind, _, slug = address.partition("/")
        if slug and kind in KINDS:
            models = [KINDS[kind]]
        else:
            slug, models = address, [Band, Artist]
        found = []
        for model in models:
            # all of them, held ones too: they're off the index already, so marking is harmless
            found.extend(model.objects.filter(slug=slug))
        return found
