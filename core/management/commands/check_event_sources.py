import csv
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from core.event_sources import CSV_COLUMNS, event_source_csv_row, save_event_source
from core.models import Venue
from core.job_runs import RecordedCommand
from django.core.management.base import BaseCommand
from django.db import transaction

"""
for each venue's website, figure out how its events could be fetched, and save the answer
in the database (VenueEventSource), where match_ticketmaster_venues and fetch_events read it.

run as:

python manage.py check_event_sources [--state NY] [--limit 20] [--csv event_sources.csv]

a run replaces the saved results of the venues it checks, and leaves every other venue's
alone, so a --state or --limit run doesn't lose the rest. --csv also writes this run's
results to a file, in the old report's columns, for people to read.

for each venue, the homepage and (if one is linked) its events page are fetched, and
checked for, in order of preference:

- ical: an ical feed with at least one event in it
- json-ld: schema.org Event data embedded in the page
- ticketing: links/embeds to a ticketing platform (dice, eventbrite, ...)
- ai-extraction: the page loads, but none of the above -- events would have to be
  extracted from the page's text

pages are fetched without running javascript, so events that are rendered client side
are missed. such pages are flagged with js_heavy.
"""

# an honest bot user agent, in the standard "compatible" crawler format --
# many sites' firewalls reject a bare python-requests user agent outright
USER_AGENT = "Mozilla/5.0 (compatible; venue-db-event-check/1.0)"
TIMEOUT_SECONDS = 15

SOCIAL_DOMAINS = ("facebook.com", "instagram.com", "linktr.ee")

TICKETING_PLATFORMS = {
    "dice": ("dice.fm",),
    "eventbrite": ("eventbrite.com", "eventbrite.co"),
    "ticketmaster": ("ticketmaster.com", "livenation.com"),
    "ticketweb": ("ticketweb.com",),
    "etix": ("etix.com",),
    "seetickets": ("seetickets.us", "seetickets.com"),
    "tixr": ("tixr.com",),
    "axs": ("axs.com",),
    "showclix": ("showclix.com",),
    "venuepilot": ("venuepilot.com", "venuepilot.co"),
    "prekindle": ("prekindle.com",),
    "opendate": ("opendate.io",),
    "ticketleap": ("ticketleap.com",),
    "brownpapertickets": ("brownpapertickets.com",),
    "squadup": ("squadup.com",),
    "songkick": ("songkick.com",),
    "bandsintown": ("bandsintown.com",),
}

EVENTS_PAGE_LINK_RE = re.compile(
    r"\b(events?|shows?|calendar|concerts?|line-?up|schedule|music|tickets|gigs)\b",
    re.IGNORECASE,
)

# link text of a site's events listing in its navigation
EVENTS_NAV_TEXT_RE = re.compile(
    r"^(upcoming |live |all )?(events?|shows?|calendar|concerts?|music|line-?up|schedule|gigs)"
    r"( calendar| & tickets| schedule)?$",
    re.IGNORECASE,
)

# a date in a url path: 10-24-2026, 2026-10-24, /2026/10/24
SINGLE_EVENT_DATE_RE = re.compile(
    r"\b\d{1,2}-\d{1,2}-\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b|/\d{4}/\d{1,2}/\d{1,2}\b"
)

# venues often use "events" for renting out the space, not for shows
PRIVATE_EVENTS_RE = re.compile(
    r"private|rental|rent\b|our-?spaces|book(ing)?-?(the|your|a|an)?-?(venue|space|party|event)"
    r"|wedding|parties|party-?packages|catering|hire|corporate",
    re.IGNORECASE,
)

FILE_LINK_RE = re.compile(
    r"\.(jpe?g|png|gif|webp|svg|pdf|mp3|mp4|zip|docx?)$", re.IGNORECASE
)


def domain_of(url):
    return urlparse(url).netloc.lower().removeprefix("www.")


def is_social(url):
    return any(domain_of(url).endswith(d) for d in SOCIAL_DOMAINS)


def normalize_url(url):
    url = url.strip()
    if url and not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    return url


def robots_allows(session, url):
    parts = urlparse(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        r = session.get(robots_url, timeout=TIMEOUT_SECONDS)
    except requests.RequestException:
        return True
    if r.status_code != 200:
        return True
    parser = RobotFileParser()
    parser.parse(r.text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


def count_json_ld_events(soup):
    def is_event(node):
        types = node.get("@type", [])
        types = types if isinstance(types, list) else [types]
        return any(isinstance(t, str) and t.endswith("Event") for t in types)

    def walk(node):
        if isinstance(node, list):
            return sum(walk(item) for item in node)
        if isinstance(node, dict):
            own = 1 if is_event(node) else 0
            return own + sum(walk(value) for value in node.values())
        return 0

    count = 0
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            count += walk(json.loads(script.string or ""))
        except (json.JSONDecodeError, TypeError):
            continue
    return count


def find_ical_urls(soup, page_url):
    urls = []
    for tag in soup.find_all(["a", "link"], href=True):
        href = tag["href"]
        if (
            tag.get("type") == "text/calendar"
            or href.lower().startswith("webcal:")
            or ".ics" in href.lower()
            or "ical=" in href.lower()
        ):
            href = re.sub(r"^webcal:", "https:", href, flags=re.IGNORECASE)
            urls.append(urljoin(page_url, href))
    return list(dict.fromkeys(urls))


def find_platforms(html):
    html = html.lower()
    return sorted(
        name
        for name, domains in TICKETING_PLATFORMS.items()
        if any(d in html for d in domains)
    )


def looks_like_single_event_page(path):
    """e.g. /products/events/jazz-jam-saturday-10-24-2026-4-00-pm-53552652 or /events/12345"""
    last_segment = path.rstrip("/").rsplit("/", 1)[-1]
    return bool(
        SINGLE_EVENT_DATE_RE.search(path)
        or re.search(r"\d{5,}", last_segment)
        or len(last_segment) > 40
    )


def find_events_page_url(soup, page_url):
    """
    the site's events listing page, or None when there isn't a separate one (e.g. the
    homepage lists the events itself and links to one page per event)
    """
    site_domain = domain_of(page_url)
    candidates = []
    for a in soup.find_all("a", href=True):
        href = urljoin(page_url, a["href"]).split("#")[0]
        parts = urlparse(href)
        path = parts.path
        if domain_of(href) != site_domain or href.rstrip("/") == page_url.rstrip("/"):
            continue
        if FILE_LINK_RE.search(path) or looks_like_single_event_page(path):
            continue
        text = a.get_text(" ", strip=True)
        if PRIVATE_EVENTS_RE.search(path) or PRIVATE_EVENTS_RE.search(text):
            continue
        text_matches = EVENTS_PAGE_LINK_RE.search(text)
        path_matches = EVENTS_PAGE_LINK_RE.search(path.replace("/", " "))
        if not (text_matches or path_matches):
            continue
        # the more of these agree, the likelier it's the listing: a link that just says
        # "Events"/"Calendar", whose text mentions events, and whose path does too
        score = (
            bool(EVENTS_NAV_TEXT_RE.match(text)) + bool(text_matches) + bool(path_matches)
        )
        in_nav = a.find_parent(["nav", "header"]) is not None
        depth = len([segment for segment in path.split("/") if segment])
        candidates.append(
            (-score, 0 if in_nav else 1, bool(parts.query), depth, len(path), href)
        )
    return min(candidates)[-1] if candidates else None


def count_ical_events(session, url):
    try:
        r = session.get(url, timeout=TIMEOUT_SECONDS)
    except requests.RequestException:
        return None
    if not r.ok or "BEGIN:VCALENDAR" not in r.text[:1000]:
        return None
    return r.text.count("BEGIN:VEVENT")


def analyze_page(html, url):
    # html.parser copes with malformed attributes that make the lxml parser crash
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        # a tag nested in an already removed tag (e.g. a script in a noscript) is gone
        if tag.decomposed:
            continue
        if tag.get("type") != "application/ld+json":
            tag.decompose()
    return {
        "soup": soup,
        "json_ld_events": count_json_ld_events(soup),
        "ical_urls": find_ical_urls(soup, url),
        "platforms": find_platforms(html),
        "uses_wp_events_calendar": "tribe-events" in html,
        "text_length": len(soup.get_text(" ", strip=True)),
    }


def check_venue(venue):
    try:
        return check_venue_unsafe(venue)
    except Exception as e:
        # one odd website shouldn't stop the whole run
        return {
            "sheet_id": venue["sheet_id"],
            "name": venue["name"],
            "state": venue["state"],
            "city_town": venue["city_town"],
            "url": venue["website"] or venue["booking_url"],
            "best_source": "check-failed",
            "error": f"{type(e).__name__}: {e}"[:200],
        }


def check_venue_unsafe(venue):
    result = {
        "sheet_id": venue["sheet_id"],
        "name": venue["name"],
        "state": venue["state"],
        "city_town": venue["city_town"],
        "url": "",
        "events_page": "",
        "best_source": "",
        "json_ld_events": 0,
        "ical_url": "",
        "ical_events": "",
        "platforms": "",
        "js_heavy": "",
        "error": "",
    }

    url = normalize_url(venue["website"] or venue["booking_url"])
    result["url"] = url
    if not url:
        result["best_source"] = "no-website"
        return result
    if is_social(url):
        result["best_source"] = "social-only"
        return result

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    session.headers["Accept"] = "text/html,application/xhtml+xml,*/*;q=0.8"

    if not robots_allows(session, url):
        result["best_source"] = "robots-blocked"
        return result

    try:
        r = session.get(url, timeout=TIMEOUT_SECONDS)
        # the sheet often links to an events page that has since moved -- fall back
        # to the site's homepage
        if r.status_code in (404, 410) and urlparse(url).path.strip("/"):
            parts = urlparse(url)
            r = session.get(f"{parts.scheme}://{parts.netloc}/", timeout=TIMEOUT_SECONDS)
        r.raise_for_status()
    except requests.RequestException as e:
        if "NameResolutionError" in str(e):
            # the domain no longer exists -- the venue has likely closed
            result["best_source"] = "dead-domain"
        elif isinstance(e, requests.HTTPError) and e.response.status_code in (403, 406, 429):
            result["best_source"] = "bot-blocked"
        else:
            result["best_source"] = "unreachable"
        result["error"] = str(e)[:200]
        return result

    # record the page that actually loaded (after redirects or the homepage fallback),
    # as fetch_events fetches it again
    result["url"] = r.url

    pages = [analyze_page(r.text, r.url)]

    events_page_url = find_events_page_url(pages[0]["soup"], r.url)
    if events_page_url and robots_allows(session, events_page_url):
        try:
            events_r = session.get(events_page_url, timeout=TIMEOUT_SECONDS)
            if events_r.ok:
                result["events_page"] = events_r.url
                pages.append(analyze_page(events_r.text, events_r.url))
            else:
                result["error"] = f"events page {events_page_url}: {events_r.status_code}"
        except requests.RequestException as e:
            result["error"] = f"events page {events_page_url}: {e}"[:200]

    ical_urls = [u for page in pages for u in page["ical_urls"]]
    if any(page["uses_wp_events_calendar"] for page in pages):
        # the events calendar wordpress plugin serves an ical feed of upcoming events here
        ical_urls.append(urljoin(r.url, "/events/?ical=1"))
    for ical_url in list(dict.fromkeys(ical_urls))[:3]:
        nmb_events = count_ical_events(session, ical_url)
        if nmb_events:
            result["ical_url"] = ical_url
            result["ical_events"] = nmb_events
            break

    result["json_ld_events"] = max(page["json_ld_events"] for page in pages)
    result["platforms"] = ";".join(sorted({p for page in pages for p in page["platforms"]}))
    # very little text without javascript usually means the page is rendered client side
    result["js_heavy"] = "yes" if max(page["text_length"] for page in pages) < 500 else ""

    if result["ical_url"]:
        result["best_source"] = "ical"
    elif result["json_ld_events"]:
        result["best_source"] = "json-ld"
    elif result["platforms"]:
        result["best_source"] = "ticketing"
    else:
        result["best_source"] = "ai-extraction"
    return result


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--csv", help="also write this run's results to this csv file")
        parser.add_argument("--state", help="only check venues in this state, e.g. NY")
        parser.add_argument("--limit", type=int)
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            help="also check venues marked inactive in the sheet",
        )
        parser.add_argument("--workers", type=int, default=16)

    def handle(self, *args, **options):
        venues = Venue.objects.order_by("sheet_id")
        if not options["include_inactive"]:
            venues = venues.exclude(is_active=False)
        if options["state"]:
            venues = venues.filter(state=options["state"].upper())
        venues = list(
            venues.values("pk", "sheet_id", "name", "state", "city_town", "website", "booking_url")
        )
        if options["limit"]:
            venues = venues[: options["limit"]]

        self.stdout.write(f"checking {len(venues)} venues...")

        results = []
        with ThreadPoolExecutor(max_workers=options["workers"]) as executor:
            futures = {executor.submit(check_venue, venue): venue["pk"] for venue in venues}
            for i, future in enumerate(as_completed(futures), start=1):
                results.append((futures[future], future.result()))
                if i % 50 == 0:
                    self.stdout.write(f"  {i}/{len(venues)}")

        results.sort(key=lambda pk_and_result: pk_and_result[1]["sheet_id"] or "")
        # saved together at the end: a crawl that dies halfway leaves the previous results
        venues_by_pk = Venue.objects.in_bulk([pk for pk, _ in results])
        with transaction.atomic():
            sources = [save_event_source(venues_by_pk[pk], result) for pk, result in results]

        if options["csv"]:
            with open(options["csv"], "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                writer.writerows(event_source_csv_row(source) for source in sources)

        counts = {}
        for _, result in results:
            counts[result["best_source"]] = counts.get(result["best_source"], 0) + 1
        for source, count in sorted(counts.items(), key=lambda item: -item[1]):
            self.stdout.write(f"{source:16} {count}")
        self.job_summary = [("venues checked", len(results))] + sorted(
            counts.items(), key=lambda item: -item[1]
        )
        self.stdout.write(self.style.SUCCESS(f"saved {len(sources)} results"))
        if options["csv"]:
            self.stdout.write(self.style.SUCCESS(f"wrote {options['csv']}"))
