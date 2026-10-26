import os
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from core.event_fetching.classification import classify
from core.event_fetching.eventbrite import EventbriteClient, EventbriteError, is_at_venue
from core.event_fetching.eventbrite import to_event_dict as eventbrite_event
from core.event_fetching.spider import SCRAPY_SETTINGS, VenueEventsSpider
from core.event_fetching.ticketmaster import TicketmasterClient, TicketmasterError
from core.event_fetching.ticketmaster import to_event_dict as ticketmaster_event
from core.event_sources import event_source_row
from core.models import Event, Venue, VenueEventSource, VenueFetchStatus
from core.job_runs import RecordedCommand
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.html import escape
from scrapy.crawler import CrawlerProcess

"""
fetches upcoming events from venue websites and saves them as unapproved events,
for an admin to review.

run as:

python manage.py fetch_events [--per-source 3 | --all] [--skip-ai] [--skip-ticketmaster] [--skip-eventbrite] [--dry-run]

venues and how to fetch their events come from the results check_event_sources saved
(VenueEventSource); a venue that has never been checked is skipped, unless it's linked to
ticketmaster or eventbrite.
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
  venues the source check found no usable source for. the venue's upcoming unapproved ical
  events are then removed, as they'd duplicate ticketmaster's. pass --skip-ticketmaster
  to fetch linked venues from their saved source instead.
- eventbrite: the eventbrite api, for venues linked to their eventbrite organizer (see
  match_eventbrite_organizers; needs EVENTBRITE_API_KEY), keeping only the organizer's
  events at the venue. it comes after ticketmaster, and replaces a linked venue's ticketing
  or ai source -- but not its ical feed or json-ld. events left over from the old source
  aren't removed, but counted in the report. pass --skip-eventbrite to fetch linked
  venues from their saved source instead.

when a linked venue's ical feed or json-ld fails on a run (no events and an error, as when
its site blocks the server), it's fetched from its api in that run instead: ticketmaster,
then eventbrite. the failure is then only noted, not counted as a problem, and the
venue's ical events are kept, as the feed should work again.

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


# notes that mean something went wrong, as opposed to informational ones (a truncated
# page, events hidden as not music). every failure note starts with one of these
PROBLEM_PREFIXES = (
    "failed:",
    "ticketmaster failed:",
    "eventbrite failed:",
    "ai extraction failed:",
)


# the saved sources whose failure falls back to the venue's linked api (a linked api
# already replaces ticketing and ai sources)
FALLBACK_SOURCES = ("ical", "json-ld")


def is_problem(note):
    return note.startswith(PROBLEM_PREFIXES)


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
        "eventbrite_organizer_id": venue.eventbrite_organizer_id or "",
    }


def select_targets(per_source, sheet_ids, all_venues, use_ticketmaster=True, use_eventbrite=True):
    sources = VenueEventSource.objects.select_related("venue").order_by("venue__sheet_id")
    if not sources.exists():
        raise CommandError("no event sources saved -- run check_event_sources first")
    rows = [event_source_row(source) for source in sources]

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
            if source == "json-ld" and row["json_ld_events"] < 3:
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
        # an eventbrite organizer is the venue selling its own shows, but a feed or json-ld
        # covers more than its eventbrite listings
        elif use_eventbrite and venue.eventbrite_organizer_id and source not in ("ical", "json-ld"):
            source = "eventbrite"
        if source is not None:
            targets.append(make_target(venue, source, row))

    if sheet_ids or all_venues:
        # linked venues with no usable saved source, e.g. bot-blocked sites or never
        # checked. ticketmaster first, so a venue linked to both is fetched from it
        api_links = [
            ("ticketmaster", "ticketmaster_venue_id", use_ticketmaster),
            ("eventbrite", "eventbrite_organizer_id", use_eventbrite),
        ]
        seen = {target["sheet_id"] for target in targets}
        for source, field, use in api_links:
            if not use:
                continue
            linked = Venue.objects.exclude(**{f"{field}__isnull": True}).exclude(**{field: ""})
            if sheet_ids:
                linked = linked.filter(sheet_id__in=sheet_ids)
            else:
                linked = linked.exclude(is_active=False)
            for venue in linked.exclude(sheet_id__in=seen).order_by("sheet_id"):
                targets.append(make_target(venue, source))
                seen.add(venue.sheet_id)
    return targets


def normalized_title(title):
    """a title for matching copies of one show: "GRYME!" and "Gryme" are the same"""
    return re.sub(r"\W", "", (title or "").lower())


def existing_copy(venue_pk, starttime, title, saved_ids):
    """
    an imported event already saved for this show under another id: the same venue,
    start time and title. ids change when a venue's source does (a scraped eventbrite
    page, then the eventbrite api) or when ai extraction words a link differently.
    hand-entered events, and copies saved earlier in this run, are never taken
    """
    key = normalized_title(title)
    candidates = (
        Event.all_objects.filter(venue_id=venue_pk, starttime=starttime)
        .exclude(source="")
        .exclude(external_id__in=saved_ids)
        .order_by("pk")
    )
    return next((event for event in candidates if normalized_title(event.title) == key), None)


def save_event(venue_pk, source, source_url, data, dry_run, saved_ids=frozenset()):
    """
    returns ("created", "updated" or "skipped"; the event's kind). saved_ids are the
    external ids this run has already saved
    """
    external_id = data["external_id"][:255]
    if not data["title"] and not data["artists"]:
        return "skipped", ""

    event = Event.all_objects.filter(external_id=external_id).first()
    adopted = False
    if event is None and data["title"]:
        event = existing_copy(venue_pk, data["starttime"], data["title"], saved_ids)
        adopted = event is not None
        if adopted:
            event.external_id = external_id
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
    # an admin's label always stands; otherwise keep the label the event already has
    # unless there's a new one
    # an adopted copy keeps its label: a fresh one for the same text could flip it
    if event.kind_set_by != Event.KindSetBy.ADMIN and data.get("kind") and not (adopted and event.kind):
        event.kind = data["kind"]
        event.kind_set_by = Event.KindSetBy.AI

    if not dry_run:
        event.save()
    return ("created" if created else "updated"), event.kind


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
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
            "--all", action="store_true", help="fetch every venue with a usable saved source"
        )
        parser.add_argument("--skip-ai", action="store_true")
        parser.add_argument(
            "--skip-ticketmaster",
            action="store_true",
            help="fetch venues linked to ticketmaster from their saved source instead",
        )
        parser.add_argument(
            "--skip-eventbrite",
            action="store_true",
            help="fetch venues linked to eventbrite from their saved source instead",
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
            options["per_source"],
            sheet_ids,
            options["all"],
            use_ticketmaster=not options["skip_ticketmaster"],
            use_eventbrite=not options["skip_eventbrite"],
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

        eventbrite_targets = [t for t in targets if t["source"] == "eventbrite"]
        self.fetch_from_eventbrite(eventbrite_targets, events_by_venue, notes_by_venue)

        results = []
        crawl_targets = [t for t in targets if t["source"] not in ("ticketmaster", "eventbrite")]
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

        fallen_back = self.fall_back_to_apis(
            crawl_targets,
            results,
            events_by_venue,
            notes_by_venue,
            options["dry_run"],
            use_ticketmaster=not options["skip_ticketmaster"],
            use_eventbrite=not options["skip_eventbrite"],
        )
        # a venue fetched from its api instead needs no ai extraction too
        pages = [
            result
            for result in results
            if result["kind"] == "page" and result["target"]["sheet_id"] not in fallen_back
        ]
        self.extract_with_ai(
            pages, options["skip_ai"], options["model"], events_by_venue, notes_by_venue
        )

        self.save_and_report(
            targets,
            events_by_venue,
            notes_by_venue,
            options["dry_run"],
            options["skip_ai"],
            options["model"],
        )

    def fall_back_to_apis(
        self, crawl_targets, results, events_by_venue, notes_by_venue, dry_run,
        use_ticketmaster=True, use_eventbrite=True,
    ):
        """
        fetches linked venues whose ical feed or json-ld failed this run -- no events and
        at least one error, as when a site blocks the server -- from their api instead.
        returns the sheet ids of the venues that fell back, whether or not the api worked
        """
        got_events = {r["target"]["sheet_id"] for r in results if r["kind"] == "events" and r["events"]}
        errored = {r["target"]["sheet_id"] for r in results if r["kind"] == "error"}
        by_api = defaultdict(list)
        for target in crawl_targets:
            sheet_id = target["sheet_id"]
            if target["source"] not in FALLBACK_SOURCES or sheet_id in got_events or sheet_id not in errored:
                continue
            # the same order as select_targets. an ical venue linked to ticketmaster
            # only gets here with --skip-ticketmaster, which turns its fallback off too
            if use_ticketmaster and target["ticketmaster_venue_id"]:
                by_api["ticketmaster"].append(target)
            elif use_eventbrite and target["eventbrite_organizer_id"]:
                by_api["eventbrite"].append(target)

        fetched = {}
        if by_api["ticketmaster"]:
            # only for this run: the feed should work again, so its events stay
            for sheet_id in self.fetch_from_ticketmaster(
                by_api["ticketmaster"], events_by_venue, notes_by_venue, dry_run, replace_ical=False
            ):
                fetched[sheet_id] = "ticketmaster"
        for sheet_id in self.fetch_from_eventbrite(by_api["eventbrite"], events_by_venue, notes_by_venue):
            fetched[sheet_id] = "eventbrite"

        for target in by_api["ticketmaster"] + by_api["eventbrite"]:
            api = fetched.get(target["sheet_id"])
            if api is None:
                # the api failed too: both failures stay problems
                continue
            notes = notes_by_venue[target["sheet_id"]]
            # the fallback worked, so the source's failure is a note, not a problem
            notes[:] = [
                f"{target['source']} failed, fetched from {api} instead: {note.removeprefix('failed: ')}"
                if note.startswith("failed: ")
                else note
                for note in notes
            ]
            target["source"] = api
        return {target["sheet_id"] for targets in by_api.values() for target in targets}

    def fetch_from_ticketmaster(
        self, targets, events_by_venue, notes_by_venue, dry_run, replace_ical=True
    ):
        """fetches targets from the ticketmaster api; returns the sheet ids it fetched"""
        fetched = set()
        if not targets:
            return fetched
        api_key = os.environ.get("TICKETMASTER_API_KEY")
        if not api_key:
            for target in targets:
                notes_by_venue[target["sheet_id"]].append(
                    "ticketmaster skipped (no TICKETMASTER_API_KEY)"
                )
            return fetched

        self.stdout.write(f"fetching {len(targets)} venues from the ticketmaster api...")
        client = TicketmasterClient(api_key)
        for target in targets:
            notes = notes_by_venue[target["sheet_id"]]
            try:
                raw_events = client.venue_events(target["ticketmaster_venue_id"])
            except TicketmasterError as e:
                notes.append(f"ticketmaster failed: {e}")
                continue
            fetched.add(target["sheet_id"])
            events = [event for event in map(ticketmaster_event, raw_events) if event]
            events_by_venue[target["sheet_id"]] += [
                ("ticketmaster", event["hyperlink"], event) for event in events
            ]
            if len(events) < len(raw_events):
                notes.append(
                    f"ticketmaster: {len(raw_events) - len(events)} non-music or undated events left out"
                )
            if replace_ical and not dry_run:
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
        return fetched

    def fetch_from_eventbrite(self, targets, events_by_venue, notes_by_venue):
        """fetches targets from the eventbrite api; returns the sheet ids it fetched"""
        fetched = set()
        if not targets:
            return fetched
        api_key = os.environ.get("EVENTBRITE_API_KEY")
        if not api_key:
            for target in targets:
                notes_by_venue[target["sheet_id"]].append(
                    "eventbrite skipped (no EVENTBRITE_API_KEY)"
                )
            return fetched

        self.stdout.write(f"fetching {len(targets)} venues from the eventbrite api...")
        client = EventbriteClient(api_key)
        venues = Venue.objects.in_bulk([target["venue_pk"] for target in targets])
        for target in targets:
            notes = notes_by_venue[target["sheet_id"]]
            venue = venues[target["venue_pk"]]
            try:
                raw_events = client.organizer_events(target["eventbrite_organizer_id"])
            except EventbriteError as e:
                notes.append(f"eventbrite failed: {e}")
                continue
            fetched.add(target["sheet_id"])
            # an organizer can be a promoter with shows at other venues too
            here = [event for event in raw_events if is_at_venue(event, venue)]
            events = [event for event in map(eventbrite_event, here) if event]
            events_by_venue[target["sheet_id"]] += [
                ("eventbrite", event["hyperlink"], event) for event in events
            ]
            if len(here) < len(raw_events):
                notes.append(f"eventbrite: {len(raw_events) - len(here)} events at other venues left out")
            if len(events) < len(here):
                notes.append(f"eventbrite: {len(here) - len(events)} online or undated events left out")
            # unlike an ical feed, scraped events can't safely be matched to these, so
            # they're left for an admin
            leftover = Event.all_objects.filter(
                venue_id=target["venue_pk"],
                source__in=[Event.Source.TICKETING, Event.Source.AI],
                is_approved=False,
                starttime__gte=timezone.now(),
            ).count()
            if leftover:
                notes.append(
                    f"{leftover} unapproved events from the venue's earlier ticketing or ai "
                    "source remain; remove any that duplicate these"
                )
        return fetched

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

        from core.event_fetching.ai_extraction import MODEL, ExtractionError, extract_events_in_parts

        client = anthropic.Anthropic()
        model = model or MODEL

        def extract(page):
            target = page["target"]
            try:
                events, usage = extract_events_in_parts(
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

    def label_events(self, chosen, skip_ai, model, notes_by_venue):
        """
        sets the kind of events that need one: new or unlabelled events, other than
        ones an admin labelled or ai extraction already labelled
        """
        external_ids = [data["external_id"][:255] for _, items in chosen for _, _, data in items]
        labelled = {
            external_id
            for external_id, kind, set_by in Event.all_objects.filter(
                external_id__in=external_ids
            ).values_list("external_id", "kind", "kind_set_by")
            if kind or set_by == Event.KindSetBy.ADMIN
        }
        needing = [
            (target, data)
            for target, items in chosen
            for source, _, data in items
            if source != "ai" and not data.get("kind") and data["external_id"][:255] not in labelled
        ]
        if not needing:
            return
        if skip_ai or not os.environ.get("ANTHROPIC_API_KEY"):
            reason = "--skip-ai" if skip_ai else "no ANTHROPIC_API_KEY"
            counts = defaultdict(int)
            for target, _ in needing:
                counts[target["sheet_id"]] += 1
            for sheet_id, count in counts.items():
                notes_by_venue[sheet_id].append(f"{count} events left unlabelled ({reason})")
            return

        # imported here so the rest of the command works without the sdk configured
        import anthropic

        from core.event_fetching.ai_extraction import MODEL

        model = model or MODEL
        self.stdout.write(f"labelling {len(needing)} events with {model}...")
        items = [
            {
                "title": data["title"],
                "artists": data["artists"],
                "description": data["description"],
                "venue": f"{target['name']} ({target['location']})",
            }
            for target, data in needing
        ]
        kinds, errors, (input_tokens, output_tokens) = classify(
            anthropic.Anthropic(), items, model=model
        )
        for (_, data), kind in zip(needing, kinds):
            data["kind"] = kind
        for error in errors:
            self.stdout.write(self.style.WARNING(error))
        self.stdout.write(
            f"labelling used {input_tokens} input / {output_tokens} output tokens"
        )

    def save_fetch_statuses(self, chosen, events_by_venue, notes_by_venue):
        """records how this fetch went for each venue, for the venue admin"""
        now = timezone.now()
        with transaction.atomic():
            for target, unique in chosen:
                VenueFetchStatus.objects.update_or_create(
                    venue_id=target["venue_pk"],
                    defaults={
                        "fetched_at": now,
                        "source": target["source"],
                        "found": len(events_by_venue[target["sheet_id"]]),
                        "upcoming": len(unique),
                        "problems": [
                            note for note in notes_by_venue[target["sheet_id"]] if is_problem(note)
                        ],
                        "job_run": getattr(self, "job_run", None),
                    },
                )

    def save_and_report(self, targets, events_by_venue, notes_by_venue, dry_run, skip_ai, model):
        now = timezone.now()
        chosen = []
        for target in targets:
            found = events_by_venue[target["sheet_id"]]
            upcoming = sorted(
                (item for item in found if item[2]["starttime"] >= now),
                key=lambda item: item[2]["starttime"],
            )
            # the same event can show up on more than one page
            unique = list({item[2]["external_id"]: item for item in upcoming}.values())
            chosen.append((target, unique[:MAX_EVENTS_PER_VENUE]))

        self.label_events(chosen, skip_ai, model, notes_by_venue)

        totals = defaultdict(int)
        kind_totals = defaultdict(int)
        saved_ids = set()
        for target, unique in chosen:
            found = events_by_venue[target["sheet_id"]]
            outcomes = defaultdict(int)
            hidden = []
            for source, source_url, data in unique:
                outcome, kind = save_event(
                    target["venue_pk"], source, source_url, data, dry_run, saved_ids
                )
                saved_ids.add(data["external_id"][:255])
                outcomes[outcome] += 1
                if outcome != "skipped":
                    kind_totals[kind or "unlabelled"] += 1
                    if kind and kind not in Event.MUSIC_KINDS:
                        hidden.append(f"{data['title']} [{kind}]")
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
            if hidden:
                self.stdout.write(f"  not music, hidden from review ({len(hidden)}): " + "; ".join(hidden))
            for note in notes_by_venue[target["sheet_id"]]:
                self.stdout.write(self.style.WARNING(f"  {note}"))

        self.job_problems = []
        for target in targets:
            problems = [note for note in notes_by_venue[target["sheet_id"]] if is_problem(note)]
            if problems:
                self.job_problems.append(
                    {
                        "venue_id": target["venue_pk"],
                        "sheet_id": target["sheet_id"],
                        "name": target["name"],
                        "problems": problems,
                    }
                )
        failed_venues = len(self.job_problems)
        if not dry_run:
            self.save_fetch_statuses(chosen, events_by_venue, notes_by_venue)
        self.job_summary = [
            ("venues", len(targets)),
            ("events created", totals["created"]),
            ("events updated", totals["updated"]),
            ("venues with failures", failed_venues),
        ]
        summary = ", ".join(f"{count} {outcome}" for outcome, count in totals.items()) or "no events"
        self.stdout.write(
            self.style.SUCCESS(f"\n{'[dry run] ' if dry_run else ''}{summary}")
        )
        if kind_totals:
            hidden_count = sum(
                count for kind, count in kind_totals.items()
                if kind != "unlabelled" and kind not in Event.MUSIC_KINDS
            )
            self.stdout.write(
                "kinds: "
                + ", ".join(f"{count} {kind}" for kind, count in sorted(kind_totals.items()))
                + f" ({hidden_count} not music, hidden from review)"
            )
