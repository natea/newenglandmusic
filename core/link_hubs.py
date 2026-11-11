"""
an act's link-hub page (linktr.ee and its rivals): which addresses are hubs, reading the
links on a page, and what to do with them (read_artist_link_hubs; add-artist-link-hub-links).

    venv/bin/python manage.py read_artist_link_hubs --limit 5 --dry-run

a page's links are read from its html and from the json some hubs embed in it
(__NEXT_DATA__), never by running a script. a link is used only when its address says what
it is (bandcamp, instagram, youtube), or, for a website, when the hub labels it so. a link
for an empty field fills it; one that differs from the record's is saved as a finding for
an editor, and nothing an editor, the import, musicbrainz or wikidata set is overwritten.
"""

import json
import re
import time
from collections import namedtuple
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from core.artists import is_bandcamp_url
from core.models import Band

LINK_HUB = "link hub"
TIMEOUT_SECONDS = 15
SECONDS_BETWEEN_REQUESTS = 1
MAX_REDIRECTS = 3
# readable: the page carries its links without javascript. a hub that turned out not to is
# kept as an address only
Hub = namedtuple("Hub", "name hosts readable")
HUBS = (
    Hub("Linktree", ("linktr.ee",), True),
    Hub("Beacons", ("beacons.ai",), False),
    Hub("Bio.link", ("bio.link",), False),
    Hub("Lnk.Bio", ("lnk.bio",), True),
    Hub("Linkin.bio", ("linkin.bio",), True),
    Hub("Solo.to", ("solo.to",), True),
    Hub("Hoo.be", ("hoo.be",), True),
    Hub("AllMyLinks", ("allmylinks.com",), True),
    Hub("Campsite", ("campsite.bio",), True),
    Hub("Taplink", ("taplink.cc",), False),
)
# first path segments that are the hub's own pages, not an act's
RESERVED = {
    "", "about", "admin", "blog", "contact", "discover", "explore", "help", "legal", "login",
    "pricing", "privacy", "register", "s", "search", "signup", "terms",
}
# the fields a hub's links can fill
FIELDS = ("website", "bandcamp_url", "instagram_url", "youtube_url")
WEBSITE_LABELS = re.compile(r"\b(website|site|homepage|official)\b", re.I)
# hosts that are never an act's own website
NOT_WEBSITES = (
    "linktr.ee", "facebook.com", "instagram.com", "twitter.com", "x.com", "tiktok.com", "threads.net",
    "youtube.com", "youtu.be", "bandcamp.com", "soundcloud.com", "spotify.com", "apple.com", "deezer.com",
    "tidal.com", "amazon.com", "pandora.com", "audiomack.com", "ticketmaster.com", "eventbrite.com",
    "seetickets.us", "etix.com", "axs.com", "dice.fm", "ticketweb.com", "seatgeek.com", "songkick.com",
    "bandsintown.com", "wikipedia.org",
)
NOT_PROFILES = {"p", "reel", "reels", "explore", "stories", "tv", "accounts", "direct", "about"}


def host_of(url):
    try:
        host = (urlsplit(url or "").hostname or "").lower()
    except ValueError:
        return ""
    return host.removeprefix("www.").removeprefix("m.")


def path_of(url):
    try:
        return urlsplit(url or "").path
    except ValueError:
        return ""


def on_host(host, domains):
    return any(host == d or host.endswith("." + d) for d in domains)


def hub_for(url):
    """the Hub whose page this is, or None: another site, or the hub's home or a reserved path"""
    try:
        parts = urlsplit((url or "").strip())
    except ValueError:
        return None
    if parts.scheme not in ("http", "https"):
        return None
    host = host_of(url)
    segments = [s for s in parts.path.split("/") if s]
    if not segments or segments[0].lower() in RESERVED:
        return None
    return next((hub for hub in HUBS if host in hub.hosts), None)


def clean_hub_url(url):
    """a hub page's address as stored (https, no query or fragment), or "" when it isn't one"""
    if hub_for(url) is None:
        return ""
    parts = urlsplit(url.strip())
    return f"https://{parts.netloc.lower()}{parts.path}"


def same_address(a, b):
    """host without www. and m., and path without case and a trailing slash; not the query"""
    return host_of(a) == host_of(b) and path_of(a).lower().rstrip("/") == path_of(b).lower().rstrip("/")


def embedded_links(node):
    """[(label, url)] from the json a hub embeds: any object with an http address"""
    found = []
    if isinstance(node, list):
        for item in node:
            found += embedded_links(item)
    elif isinstance(node, dict):
        url = node.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            label = next((node[k] for k in ("title", "name", "label", "text") if isinstance(node.get(k), str)), "")
            found.append((label, url))
        for value in node.values():
            if isinstance(value, (list, dict)):
                found += embedded_links(value)
    return found


def links_on(html):
    """[(label, url)] on a hub page, from its anchors and its embedded json, without repeats"""
    soup = BeautifulSoup(html or "", "html.parser")
    found = []
    for script in soup.find_all("script"):
        if script.get("type") == "application/json" or script.get("id") == "__NEXT_DATA__":
            try:
                found += embedded_links(json.loads(script.string or ""))
            except ValueError:
                continue
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if href.startswith(("http://", "https://")):
            found.append((" ".join(anchor.get_text().split()), href))
    unique = {}
    for label, url in found:
        # an anchor often repeats an embedded link, with the label the page shows
        if url not in unique or (label and not unique[url]):
            unique[url] = label
    return [(label, url) for url, label in unique.items()]


def has_script(html):
    """whether the page has a script that isn't data: its links may be built in the browser"""
    soup = BeautifulSoup(html or "", "html.parser")
    return any(
        s.get("type") not in ("application/json", "application/ld+json") and s.get("id") != "__NEXT_DATA__"
        for s in soup.find_all("script")
    )


def is_instagram(url):
    segments = [s for s in path_of(url).split("/") if s]
    return (
        url.startswith("https://") and host_of(url) == "instagram.com"
        and len(segments) == 1 and segments[0].lower() not in NOT_PROFILES
    )


def is_youtube(url):
    segments = [s for s in path_of(url).split("/") if s]
    if not url.startswith("https://") or host_of(url) != "youtube.com" or not segments:
        return False
    return (segments[0].startswith("@") and len(segments[0]) > 1) or (
        segments[0] in ("channel", "c", "user") and len(segments) > 1
    )


def is_website(label, url):
    return (
        url.startswith(("http://", "https://")) and bool(WEBSITE_LABELS.search(label or ""))
        and not on_host(host_of(url), NOT_WEBSITES) and not any(host_of(url) in hub.hosts for hub in HUBS)
    )


def tidy(url):
    """the address without its query and fragment"""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


def classify(links):
    """{field: [addresses]} for the links an address (or, for a website, a label) identifies.
    an address too long for its field is left out"""
    found = {field: [] for field in FIELDS}
    for label, url in links:
        if is_bandcamp_url(url):
            field = "bandcamp_url"
        elif is_instagram(url):
            field = "instagram_url"
        elif is_youtube(url):
            field = "youtube_url"
        elif is_website(label, url):
            field = "website"
        else:
            continue
        url = tidy(url) if field != "website" else url
        if len(url) > Band._meta.get_field(field).max_length:
            continue
        if not any(same_address(url, other) for other in found[field]):
            found[field].append(url)
    return found


def agrees(value, candidates):
    return any(same_address(value, c) for c in candidates)


def apply(record, links, now):
    """
    what the hub's links change on the record (not saved): (changes, findings), changes being
    {field: address} to set, marked "link hub", and findings the record's new list: open ones
    for a field whose value differs from the hub's, and the dismissed ones kept
    """
    candidates = classify(links)
    dismissed = [f for f in record.link_hub_findings if f.get("dismissed")]
    changes, findings = {}, list(dismissed)
    for field in FIELDS:
        options = candidates[field]
        if not options:
            continue
        current = getattr(record, field)
        source = record.field_sources.get(field)
        hub_address = bool(current) and field == "website" and hub_for(current) is not None
        if len(options) == 1 and not hub_address and (not current or source == LINK_HUB):
            if not current or not same_address(current, options[0]):
                changes[field] = options[0]
            continue
        if current and not hub_address and agrees(current, options):
            continue
        if any(d["field"] == field and agrees(d["hub"], options) and len(d.get("options") or [1]) == len(options) for d in dismissed):
            continue
        finding = {"field": field, "current": current, "hub": options[0], "seen_at": now.isoformat(), "dismissed": False}
        if len(options) > 1:
            finding["options"] = options
        findings.append(finding)
    return changes, findings


class PoliteSession:
    """
    a requests session for hub pages: the honest user agent, one request a second, and each
    hub's robots.txt asked for once however many of its pages are read. no javascript runs
    """

    def __init__(self, user_agent, sleep=None, clock=None):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self.session.headers["Accept"] = "text/html,application/xhtml+xml,*/*;q=0.8"
        self.sleep = sleep or time.sleep
        self.clock = clock or time.monotonic
        self.last_request = None
        self.robots = {}

    def get(self, url, **kwargs):
        is_robots = path_of(url) == "/robots.txt"
        if is_robots and url in self.robots:
            answer = self.robots[url]
            if isinstance(answer, Exception):
                raise answer
            return answer
        if self.last_request is not None:
            wait = SECONDS_BETWEEN_REQUESTS - (self.clock() - self.last_request)
            if wait > 0:
                self.sleep(wait)
        try:
            answer = self.session.get(url, **kwargs)
        except requests.RequestException as e:
            answer = e
        self.last_request = self.clock()
        if is_robots:
            self.robots[url] = answer
        if isinstance(answer, Exception):
            raise answer
        return answer


def fetch(session, url):
    """
    (problem, html): the page's html, or the status that says why not: "blocked" (403, 406
    or 429), "gone" (404 or 410) or "failed" (anything else, and a redirect off the hub's
    host, which is never followed). the page is the only thing requested
    """
    origin = host_of(url)
    for _ in range(MAX_REDIRECTS + 1):
        try:
            r = session.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=False)
        except requests.RequestException:
            return "failed", ""
        if r.status_code in (301, 302, 303, 307, 308):
            url = urljoin(url, r.headers.get("Location") or "")
            if host_of(url) != origin:
                return "failed", ""
            continue
        if r.status_code in (403, 406, 429):
            return "blocked", ""
        if r.status_code in (404, 410):
            return "gone", ""
        if r.status_code != 200:
            return "failed", ""
        return "", r.text
    return "failed", ""
