import csv
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from core.event_fetching.spider import SCRAPY_SETTINGS, VenueEventsSpider
from core.models import Event, Venue
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.html import escape
from scrapy.crawler import CrawlerProcess

"""
fetches upcoming events from venue websites and saves them as unapproved events,
for an admin to review.

run as:

python manage.py fetch_events [--report event_sources.csv] [--per-source 3 | --all] [--dry-run]

venues and how to fetch their events come from the csv written by check_event_sources.
by default, the first --per-source venues of each kind are fetched (a pilot); --all
fetches every venue whose events can be fetched in one of these ways:

- ical: the venue's ical feed
- json-ld: schema.org event data on the venue's site
- ticketing: event pages on ticketing platforms that the venue's site links to
- ai: the venue's events page, with events extracted by claude (needs ANTHROPIC_API_KEY;
  claude-haiku-5-5 by default, or pass --model)

events are matched on external_id, so re-running updates events instead of duplicating
them. new events are saved unapproved; already-approved events stay approved.
"""

MAX_EVENTS_PER_VENUE = 50
AI_EXTRACTION_WORKERS = 8

REPORT_SOURCE_TO_TARGET_SOURCE = {
    "ical": "ical",
    "json-ld": "json-ld",
    "ticketing": "ticketing",
    "ai-extraction": "ai",
}


def price_bucket(amount):
    """maps a ticket price onto the site's price ranges"""
    if amount is None:
        return None
    if amount == 0:
        return "🌀 free"
    if amount < 30:
        return "$"
    if amount < 50:
        return "$$"
    if amount < 75:
        return "$$$"
    return "$$$$"


def short(value, max_length=255):
    """a char field value, or "" when it doesn't fit (e.g. a very long url)"""
    value = (value or "").strip()
    return value if len(value) <= max_length else ""


def select_targets(report_path, per_source, sheet_ids, all_venues):
    try:
        with open(report_path) as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        raise CommandError(f"{report_path} not found -- run check_event_sources first")

    if sheet_ids:
        rows = [row for row in rows if row["sheet_id"] in sheet_ids]
    elif all_venues:
        rows = [row for row in rows if row["best_source"] in REPORT_SOURCE_TO_TARGET_SOURCE]
    else:
        picked = defaultdict(list)
        for row in rows:
            source = row["best_source"]
            if source not in REPORT_SOURCE_TO_TARGET_SOURCE or len(picked[source]) >= per_source:
                continue
            # for the pilot, prefer venues that are likely to work for their kind
            if source == "json-ld" and int(row["json_ld_events"] or 0) < 3:
                continue
            if source == "ai-extraction" and (not row["events_page"] or row["js_heavy"]):
                continue
            picked[source].append(row)
        rows = [row for source_rows in picked.values() for row in source_rows]

    venues = Venue.objects.in_bulk([row["sheet_id"] for row in rows], field_name="sheet_id")
    targets = []
    for row in rows:
        venue = venues.get(row["sheet_id"])
        source = REPORT_SOURCE_TO_TARGET_SOURCE.get(row["best_source"])
        if venue is None or source is None:
            continue
        targets.append(
            {
                "venue_pk": venue.pk,
                "sheet_id": row["sheet_id"],
                "name": venue.name,
                "location": venue.location,
                "source": source,
                "url": row["url"],
                "events_page": row["events_page"],
                "ical_url": row["ical_url"],
            }
        )
    return targets


def save_event(venue_pk, source, source_url, data, dry_run):
    """returns "created", "updated" or "skipped" """
    external_id = data["external_id"][:255]
    if not data["title"] and not data["artists"]:
        return "skipped"

    event = Event.all_objects.filter(external_id=external_id).first()
    created = event is None
    if created:
        event = Event(external_id=external_id, is_approved=False)

    event.venue_id = venue_pk
    event.source = source
    event.source_url = source_url
    event.title = short(data["title"])
    event.artists = short(data["artists"])
    event.starttime = data["starttime"]
    event.starttime_override = "time TBA" if data["all_day"] else None
    # descriptions come from other websites and are shown unescaped on the calendar
    event.description = escape(data["description"]) or None
    event.hyperlink = short(data["hyperlink"]) or None
    event.ticket_hyperlink = short(data["ticket_hyperlink"]) or None
    event.price = price_bucket(data["price_amount"])
    event.is_cancelled = data["is_cancelled"]

    if not dry_run:
        event.save()
    return "created" if created else "updated"


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--report", default="event_sources.csv")
        parser.add_argument(
            "--per-source",
            type=int,
            default=3,
            help="how many venues of each kind to fetch",
        )
        parser.add_argument(
            "--sheet-ids",
            help="comma-separated Venue_IDs to fetch, instead of picking per source",
        )
        parser.add_argument(
            "--all", action="store_true", help="fetch every venue in the report"
        )
        parser.add_argument("--skip-ai", action="store_true")
        parser.add_argument(
            "--model",
            help="claude model for ai extraction (default: core.event_fetching.ai_extraction.MODEL)",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="fetch and report, but save nothing"
        )

    def handle(self, *args, **options):
        sheet_ids = set(options["sheet_ids"].split(",")) if options["sheet_ids"] else None
        targets = select_targets(
            options["report"], options["per_source"], sheet_ids, options["all"]
        )
        if not targets:
            raise CommandError("no venues to fetch")

        self.stdout.write(f"fetching events for {len(targets)} venues...")
        results = []
        process = CrawlerProcess(settings=SCRAPY_SETTINGS)
        process.crawl(VenueEventsSpider, targets=targets, results=results)
        process.start()

        events_by_venue = defaultdict(list)
        notes_by_venue = defaultdict(list)
        for result in results:
            target = result["target"]
            if result["kind"] == "events":
                events_by_venue[target["sheet_id"]] += [
                    (result["source"], result["url"], event) for event in result["events"]
                ]
            elif result["kind"] == "error":
                notes_by_venue[target["sheet_id"]].append(f"failed: {result['url']} {result['error']}")

        pages = [result for result in results if result["kind"] == "page"]
        self.extract_with_ai(
            pages, options["skip_ai"], options["model"], events_by_venue, notes_by_venue
        )

        self.save_and_report(targets, events_by_venue, notes_by_venue, options["dry_run"])

    def extract_with_ai(self, pages, skip_ai, model, events_by_venue, notes_by_venue):
        if not pages:
            return
        if skip_ai or not os.environ.get("ANTHROPIC_API_KEY"):
            reason = "--skip-ai" if skip_ai else "no ANTHROPIC_API_KEY"
            for page in pages:
                notes_by_venue[page["target"]["sheet_id"]].append(
                    f"ai extraction skipped ({reason}): {len(page['text'])} chars of page text"
                )
            return

        # imported here so the rest of the command works without the sdk configured
        import anthropic

        from core.event_fetching.ai_extraction import MODEL, ExtractionError, extract_events

        client = anthropic.Anthropic()
        model = model or MODEL

        def extract(page):
            target = page["target"]
            try:
                events, usage = extract_events(
                    client,
                    target["name"],
                    target["location"],
                    page["url"],
                    page["text"],
                    model=model,
                )
            except (anthropic.APIError, ExtractionError, ValueError) as e:
                return page, [], None, e
            return page, events, usage, None

        self.stdout.write(f"extracting events from {len(pages)} pages with {model}...")
        input_tokens = output_tokens = 0
        with ThreadPoolExecutor(max_workers=AI_EXTRACTION_WORKERS) as executor:
            for page, events, usage, error in executor.map(extract, pages):
                notes = notes_by_venue[page["target"]["sheet_id"]]
                if page["truncated"]:
                    notes.append("page text was truncated for ai extraction")
                if error:
                    notes.append(f"ai extraction failed: {error}"[:200])
                    continue
                events_by_venue[page["target"]["sheet_id"]] += [
                    ("ai", page["url"], event) for event in events
                ]
                notes.append(
                    f"ai ({model}): {usage.input_tokens} input / {usage.output_tokens} output tokens"
                )
                input_tokens += usage.input_tokens
                output_tokens += usage.output_tokens
        self.stdout.write(
            f"ai extraction used {input_tokens} input / {output_tokens} output tokens"
        )

    def save_and_report(self, targets, events_by_venue, notes_by_venue, dry_run):
        now = timezone.now()
        totals = defaultdict(int)
        for target in targets:
            found = events_by_venue[target["sheet_id"]]
            upcoming = sorted(
                (item for item in found if item[2]["starttime"] >= now),
                key=lambda item: item[2]["starttime"],
            )
            # the same event can show up on more than one page
            unique = list({item[2]["external_id"]: item for item in upcoming}.values())
            unique = unique[:MAX_EVENTS_PER_VENUE]

            outcomes = defaultdict(int)
            for source, source_url, data in unique:
                outcomes[save_event(target["venue_pk"], source, source_url, data, dry_run)] += 1
            for outcome, count in outcomes.items():
                totals[outcome] += count

            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"\n{target['sheet_id']} {target['name']} ({target['location']}) [{target['source']}]"
                )
            )
            self.stdout.write(
                f"  {len(found)} found, {len(unique)} upcoming"
                + "".join(f", {count} {outcome}" for outcome, count in outcomes.items())
            )
            for _, _, data in unique[:3]:
                when = data["starttime"].astimezone(timezone.get_current_timezone())
                when = when.strftime("%a %b %-d" if data["all_day"] else "%a %b %-d %-I:%M%p")
                artists = f" -- {data['artists']}" if data["artists"] else ""
                price = f" [{price_bucket(data['price_amount'])}]" if data["price_amount"] is not None else ""
                self.stdout.write(f"    {when}  {data['title']}{artists}{price}")
            for note in notes_by_venue[target["sheet_id"]]:
                self.stdout.write(self.style.WARNING(f"  {note}"))

        summary = ", ".join(f"{count} {outcome}" for outcome, count in totals.items()) or "no events"
        self.stdout.write(
            self.style.SUCCESS(f"\n{'[dry run] ' if dry_run else ''}{summary}")
        )
