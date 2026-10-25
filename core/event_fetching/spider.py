"""
a scrapy spider that fetches events for a list of venues.

the spider only collects data into `results` -- it never touches the database, as
scrapy runs on an async reactor where django's orm can't be used. the fetch_events
command saves the results once the crawl is done.

each result is a dict with a "kind":
- "events": parsed event dicts (see parsing.py) for a target
- "page": cleaned page text for a target, to be handed to ai extraction
- "error": a request that failed
"""

import re
from urllib.parse import urljoin, urlparse

import scrapy
from bs4 import BeautifulSoup
from core.management.commands.check_event_sources import (
    TICKETING_PLATFORMS,
    USER_AGENT,
)

from core.event_fetching.parsing import (
    is_opendate_url,
    is_placeholder_midnight,
    parse_ical,
    parse_json_ld,
    with_opendate_time,
)

MAX_TICKETING_EVENT_PAGES = 10
# opendate pages to check for real start times, per venue page; the import keeps at most
# 50 events per venue anyway
MAX_OPENDATE_TIME_CHECKS = 50
MAX_PAGE_TEXT_LENGTH = 150_000

TICKETING_DOMAINS = tuple(d for domains in TICKETING_PLATFORMS.values() for d in domains)
# platforms that refuse crawlers and then block the whole IP, ticket buyers included.
# ticketmaster events come from its discovery api instead (match_ticketmaster_venues)
UNCRAWLABLE_DOMAINS = ("tixr.com", "ticketmaster.com")
# paths that look like a single event's page on a ticketing platform
TICKETING_EVENT_PATH_RE = re.compile(r"/(e|events?|ticket)/", re.IGNORECASE)

SCRAPY_SETTINGS = {
    "USER_AGENT": USER_AGENT,
    "ROBOTSTXT_OBEY": True,
    "AUTOTHROTTLE_ENABLED": True,
    "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    "DOWNLOAD_DELAY": 0.5,
    "DOWNLOAD_TIMEOUT": 20,
    "RETRY_TIMES": 1,
    "LOG_LEVEL": "WARNING",
}


def is_ticketing_event_url(url):
    parts = urlparse(url)
    host = parts.netloc.lower().removeprefix("www.")
    if any(host.endswith(d) for d in UNCRAWLABLE_DOMAINS):
        return False
    return any(host.endswith(d) for d in TICKETING_DOMAINS) and bool(
        TICKETING_EVENT_PATH_RE.search(parts.path)
    )


def page_text_for_ai(html, base_url):
    """the page's visible text, with link urls kept next to their text"""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "head"]):
        if not tag.decomposed:
            tag.decompose()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if a.get_text(strip=True) and href.startswith(("http", "/")):
            a.append(f" <{urljoin(base_url, href)}>")
    lines = (line.strip() for line in soup.get_text("\n").splitlines())
    return "\n".join(line for line in lines if line)


class VenueEventsSpider(scrapy.Spider):
    name = "venue_events"

    def __init__(self, targets, results, **kwargs):
        super().__init__(**kwargs)
        self.targets = targets
        self.results = results

    async def start(self):
        for target in self.targets:
            pages = list(dict.fromkeys(u for u in [target["events_page"], target["url"]] if u))
            if target["source"] == "ical":
                urls, callback = [target["ical_url"]], self.parse_ical
            elif target["source"] == "json-ld":
                urls, callback = pages, self.parse_json_ld
            elif target["source"] == "ticketing":
                urls, callback = pages, self.parse_ticketing_listing
            else:
                urls, callback = pages[:1], self.parse_page_for_ai
            for url in urls:
                yield scrapy.Request(
                    url,
                    callback=callback,
                    errback=self.on_error,
                    cb_kwargs={"target": target},
                    dont_filter=True,
                )

    def add_events(self, target, events, url, source):
        self.results.append(
            {"kind": "events", "target": target, "events": events, "url": url, "source": source}
        )

    def parse_ical(self, response, target):
        try:
            events = parse_ical(response.body, response.url)
        except Exception as e:
            # some feeds are malformed in ways the icalendar library can't handle
            # (e.g. a list where it expects a timezone id) -- fall back to ai extraction
            # of the venue's events page
            self.results.append(
                {
                    "kind": "error",
                    "target": target,
                    "url": response.url,
                    "error": f"unparseable ical feed, falling back to ai: {e!r}"[:200],
                }
            )
            page_url = target["events_page"] or target["url"]
            if page_url:
                yield scrapy.Request(
                    page_url,
                    callback=self.parse_page_for_ai,
                    errback=self.on_error,
                    cb_kwargs={"target": target},
                    dont_filter=True,
                )
            return
        self.add_events(target, events, response.url, "ical")

    def parse_json_ld(self, response, target):
        scripts = response.xpath('//script[@type="application/ld+json"]/text()').getall()
        events = parse_json_ld(scripts, response.url)
        # venue sites listing opendate's events may give "midnight" for "no time"; the
        # opendate page has the real time, so those events wait for it
        placeholders = [event for event in events if is_placeholder_midnight(event)]
        to_check = placeholders[:MAX_OPENDATE_TIME_CHECKS]
        ready = [event for event in events if not is_placeholder_midnight(event)]
        ready += [{**event, "all_day": True} for event in placeholders[MAX_OPENDATE_TIME_CHECKS:]]
        self.add_events(target, ready, response.url, "json-ld")
        for event in to_check:
            yield scrapy.Request(
                event["ticket_hyperlink"],
                callback=self.parse_opendate_time,
                errback=self.on_opendate_time_error,
                cb_kwargs={"target": target, "event": event, "page_url": response.url},
                dont_filter=True,
            )

    def parse_opendate_time(self, response, target, event, page_url):
        self.add_events(target, [with_opendate_time(event, response.text)], page_url, "json-ld")

    def on_opendate_time_error(self, failure):
        # the event is still saved, as "time TBA"; the failed request is reported too
        kwargs = failure.request.cb_kwargs
        self.add_events(
            kwargs["target"], [{**kwargs["event"], "all_day": True}], kwargs["page_url"], "json-ld"
        )
        self.on_error(failure)

    def parse_ticketing_listing(self, response, target):
        event_urls = []
        for href in response.xpath("//a/@href | //iframe/@src").getall():
            url = response.urljoin(href).split("?")[0]
            if is_ticketing_event_url(url) and url not in event_urls:
                event_urls.append(url)
        for url in event_urls[:MAX_TICKETING_EVENT_PAGES]:
            yield scrapy.Request(
                url,
                callback=self.parse_ticketing_event,
                errback=self.on_error,
                cb_kwargs={"target": target},
            )

    def parse_ticketing_event(self, response, target):
        scripts = response.xpath('//script[@type="application/ld+json"]/text()').getall()
        events = parse_json_ld(scripts, response.url)
        if is_opendate_url(response.url) and len(events) == 1 and events[0]["all_day"]:
            # opendate's json-ld gives only the date; the page's own data has the time
            events = [with_opendate_time(events[0], response.text)]
        if events:
            self.add_events(target, events, response.url, "ticketing")
        else:
            # some platforms (e.g. venuepilot) have no structured data on event pages
            self.parse_page_for_ai(response, target)

    def parse_page_for_ai(self, response, target):
        text = page_text_for_ai(response.text, response.url)
        self.results.append(
            {
                "kind": "page",
                "target": target,
                "url": response.url,
                "text": text[:MAX_PAGE_TEXT_LENGTH],
                "truncated": len(text) > MAX_PAGE_TEXT_LENGTH,
            }
        )

    def on_error(self, failure):
        request = failure.request
        self.results.append(
            {
                "kind": "error",
                "target": request.cb_kwargs.get("target"),
                "url": request.url,
                "error": repr(failure.value)[:200],
            }
        )
