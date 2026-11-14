import os
from collections import defaultdict

from core.event_fetching.classification import classify
from core.models import Event
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

"""
labels existing imported events with what kind of event they are (live music, dj night,
open mic, karaoke, comedy, other), so the event review list can leave out the ones that
aren't music. new events are labelled by fetch_events as they're imported; this is for
events imported before that, or left unlabelled when labelling failed.

run as:

python manage.py classify_events [--dry-run] [--limit 100] [--model claude-haiku-5-5]

only upcoming imported events with no kind are labelled -- never one an admin labelled.
--dry-run shows the kinds it would set and every event it would hide, and saves nothing
(it still asks claude, so it costs the same as a real run). needs ANTHROPIC_API_KEY.

cost: claude-haiku-5-5, 50 events per request -- about $0.01 per 50 events.
"""


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int)
        parser.add_argument(
            "--model",
            help="claude model (default: core.event_fetching.ai_extraction.MODEL)",
        )
        parser.add_argument("--dry-run", action="store_true", help="report, but save nothing")

    def handle(self, *args, **options):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise CommandError("ANTHROPIC_API_KEY is not set")

        # imported here so the rest of the command works without the sdk configured
        import anthropic

        from core.event_fetching.ai_extraction import MODEL

        events = (
            Event.all_objects.filter(starttime__gte=timezone.now(), kind="")
            .exclude(source="")
            .exclude(kind_set_by=Event.KindSetBy.ADMIN)
            .select_related("venue")
            .order_by("starttime")
        )
        if options["limit"]:
            events = events[: options["limit"]]
        events = list(events)
        if not events:
            self.stdout.write("no events to label")
            return

        model = options["model"] or MODEL
        self.stdout.write(f"labelling {len(events)} events with {model}...")
        items = [
            {
                "title": event.title,
                "artists": event.artists,
                "description": event.description or "",
                "venue": f"{event.venue.name} ({event.venue.location})" if event.venue else "",
            }
            for event in events
        ]
        kinds, errors, (input_tokens, output_tokens) = classify(
            anthropic.Anthropic(), items, model=model
        )

        counts = defaultdict(int)
        hidden_by_venue = defaultdict(list)
        for event, kind in zip(events, kinds):
            counts[kind or "unlabelled"] += 1
            if kind and kind not in Event.MUSIC_KINDS:
                venue = f"{event.venue.name} ({event.venue.location})" if event.venue else "no venue"
                hidden_by_venue[venue].append(f"{event.title} [{kind}]")
            if kind and not options["dry_run"]:
                # update() rather than save(): the kind isn't shown on the calendar, so
                # there's no html to rebake
                Event.all_objects.filter(pk=event.pk).update(
                    kind=kind, kind_set_by=Event.KindSetBy.AI
                )

        prefix = "[dry run] " if options["dry_run"] else ""
        hidden_count = sum(len(titles) for titles in hidden_by_venue.values())
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\n{prefix}not music, {'would be ' if options['dry_run'] else ''}hidden from review ({hidden_count})"
            )
        )
        for venue, titles in sorted(hidden_by_venue.items()):
            self.stdout.write(f"  {venue}")
            for title in titles:
                self.stdout.write(f"      {title}")
        for error in errors:
            self.stdout.write(self.style.WARNING(error))
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{prefix}"
                + ", ".join(f"{count} {kind}" for kind, count in sorted(counts.items()))
            )
        )
        self.stdout.write(f"tokens: {input_tokens} input / {output_tokens} output")
