import csv
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from core.event_fetching.spider import SCRAPY_SETTINGS, VenueEventsSpider
from core.event_fetching.ticketmaster import TicketmasterClient, TicketmasterError
from core.event_fetching.ticketmaster import to_event_dict as ticketmaster_event
from core.models import Event, Venue
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.html import escape
from scrapy.crawler import CrawlerProcess

"""
fetches upcoming events from venue websites and saves them as unapproved events,
for an admin to review.

run as:

python manage.py fetch_events [--report event_sources.csv] [--per-source 3 | --all] [--skip-ai] [--skip-ticketmaster] [--dry-run]

venues and how to fetch their events come from the csv written by check_event_sources.
by default, the first --per-source venues of each kind are fetched (a pilot); --all
fetches every venue whose events can be fetched in one of these ways:

- ical: the venue's ical feed
- json-ld: schema.org event data on the venue's site
- ticketing: event pages on ticketing platforms that the venue's site links to
- ai: the venue's events page, with events extracted by claude (needs ANTHROPIC_API_KEY;
  claude-haiku-5-5 by default, or pass --model)
- ticketmaster: the ticketmaster discovery api, for venues linked to ticketmaster (see
  match_ticketmaster_venues; needs TICKETMASTER_API_KEY). it replaces a linked venue's
  ical feed, ticketing or ai source -- but not its json-ld -- and also covers linked
  venues the report found no usable source for. the venue's upcoming unapproved ical
  events are then removed, as they'd duplicate ticketmaster's. pass --skip-ticketmaster
  to fetch linked venues from their report source instead.

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


def make_target(venue, source, row=None):
    row = row or {}
    return {
        "venue_pk": venue.pk,
        "sheet_id": venue.sheet_id,
        "name": venue.name,
        "location": venue.location,
        "source": source,
        "url": row.get("url", ""),
        "events_page": row.get("events_page", ""),
        "ical_url": row.get("ical_url", ""),
        "ticketmaster_venue_id": venue.ticketmaster_venue_id or "",
    }


def select_targets(report_path, per_source, sheet_ids, all_venues, use_ticketmaster=True):
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
        if venue is None:
            continue
        source = REPORT_SOURCE_TO_TARGET_SOURCE.get(row["best_source"])
        # the ticketmaster api replaces a linked venue's ical feed, ticketing pages or ai
        # extraction -- feeds turned out to list a fraction of a venue's shows (the anthem:
        # 1 vs 42) -- but not its json-ld, which lists about as many
        if use_ticketmaster and venue.ticketmaster_venue_id and source != "json-ld":
            source = "ticketmaster"
        if source is not None:
            targets.append(make_target(venue, source, row))

    if use_ticketmaster and (sheet_ids or all_venues):
        # linked venues the report gave no usable source, e.g. bot-blocked sites
        linked = Venue.objects.exclude(ticketmaster_venue_id__isnull=True).exclude(
            ticketmaster_venue_id=""
        )
        if sheet_ids:
            linked = linked.filter(sheet_id__in=sheet_ids)
        else:
            linked = linked.exclude(is_active=False)
        seen = {target["sheet_id"] for target in targets}
        for venue in linked.exclude(sheet_id__in=seen).order_by("sheet_id"):
            targets.append(make_target(venue, "ticketmaster"))
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
            "--skip-ticketmaster",
            action="store_true",
            help="fetch venues linked to ticketmaster from their report source instead",
        )
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
            options["report"],
            options["per_source"],
            sheet_ids,
            options["all"],
            use_ticketmaster=not options["skip_ticketmaster"],
        )
        if not targets:
            raise CommandError("no venues to fetch")

        self.stdout.write(f"fetching events for {len(targets)} venues...")
        events_by_venue = defaultdict(list)
        notes_by_venue = defaultdict(list)
        ticketmaster_targets = [t for t in targets if t["source"] == "ticketmaster"]
        self.fetch_from_ticketmaster(
            ticketmaster_targets, events_by_venue, notes_by_venue, options["dry_run"]
        )

        results = []
        crawl_targets = [t for t in targets if t["source"] != "ticketmaster"]
        if crawl_targets:
            process = CrawlerProcess(settings=SCRAPY_SETTINGS)
            process.crawl(VenueEventsSpider, targets=crawl_targets, results=results)
            process.start()

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

    def fetch_from_ticketmaster(self, targets, events_by_venue, notes_by_venue, dry_run):
        if not targets:
            return
        api_key = os.environ.get("TICKETMASTER_API_KEY")
        if not api_key:
            for target in targets:
                notes_by_venue[target["sheet_id"]].append(
                    "ticketmaster skipped (no TICKETMASTER_API_KEY)"
                )
            return

        self.stdout.write(f"fetching {len(targets)} venues from the ticketmaster api...")
        client = TicketmasterClient(api_key)
        for target in targets:
            notes = notes_by_venue[target["sheet_id"]]
            try:
                raw_events = client.venue_events(target["ticketmaster_venue_id"])
            except TicketmasterError as e:
                notes.append(f"ticketmaster failed: {e}")
                continue
            events = [event for event in map(ticketmaster_event, raw_events) if event]
            events_by_venue[target["sheet_id"]] += [
                ("ticketmaster", event["hyperlink"], event) for event in events
            ]
            if len(events) < len(raw_events):
                notes.append(
                    f"ticketmaster: {len(raw_events) - len(events)} non-music or undated events left out"
                )
            if not dry_run:
                # events from the venue's ical feed, which ticketmaster replaces, would
                # duplicate these under other ids. approved ones are someone's decision
                stale, _ = Event.all_objects.filter(
                    venue_id=target["venue_pk"],
                    source=Event.Source.ICAL,
                    is_approved=False,
                    starttime__gte=timezone.now(),
                ).delete()
                if stale:
                    notes.append(f"removed {stale} unapproved events from the venue's ical feed")

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
