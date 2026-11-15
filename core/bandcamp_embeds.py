"""
reads the id of an act's bandcamp player from its own bandcamp page, for the listing's and
the act pages' embedded player (find_bandcamp_embeds):

    session = PoliteSession(USER_AGENT)
    result = lookup(session, record.bandcamp_url)      # Result(status, kind, embed_id, why)
    fields = apply(record, result, now)

only the kind (album or track) and the numeric id are taken from a page, by its structure
(json-ld and page properties for a release the page redirects to, the first music tile of a
discography grid), with no script run. merchandise tiles are skipped. a release whose
player has no streamable track (a physical-only one) is skipped for the next, three tried.
the page is requested politely: robots.txt, the event checks' honest user agent, two seconds
between requests, no proxy, and no redirect off bandcamp.com. nothing else is requested.
"""

import datetime
import json
import re
import time
from collections import namedtuple
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from core.artists import bandcamp_player_url, is_bandcamp_url, is_embed_id
from core.management.commands.check_event_sources import TIMEOUT_SECONDS, robots_allows
from core.models import MusicAct

Status = MusicAct.BandcampEmbedStatus
SECONDS_BETWEEN_REQUESTS = 2
MAX_REDIRECTS = 5
# releases tried on one page, each costing a request for its player
MAX_PLAYERS_TRIED = 3
# the player page's track data, where a streamable track has an audio "file". its "not
# available" message is always in the page, hidden until its script shows it, so the text
# can't tell a playable release from one that isn't
PLAYER_DATA_ATTRIBUTE = "data-player-data"
REFRESH_FOUND_AFTER = datetime.timedelta(days=365)
RETRY_OTHERS_AFTER = datetime.timedelta(days=90)
TILE_RE = re.compile(r"(album|track)-(\d+)")
PAGE_KINDS = {"a": "album", "t": "track"}

# what a look-up came to: a status, and for "found" the kind and id
Result = namedtuple("Result", "status kind embed_id why", defaults=("", "", ""))


class PoliteSession:
    """
    a requests session for bandcamp: the honest user agent, no proxy, two seconds between
    requests, and each host's robots.txt asked for once however many pages are read
    """

    def __init__(self, user_agent, sleep=None, clock=None):
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers["User-Agent"] = user_agent
        self.session.headers["Accept"] = "text/html,application/xhtml+xml,*/*;q=0.8"
        self.sleep = sleep or time.sleep
        self.clock = clock or time.monotonic
        self.last_request = None
        self.robots = {}

    def get(self, url, **kwargs):
        is_robots = urlsplit(url).path == "/robots.txt"
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


def as_list(value):
    return value if isinstance(value, list) else [] if value is None else [value]


def item_id_of(node):
    """the id a json-ld node gives as item_id, directly or among its additional properties"""
    if not isinstance(node, dict):
        return ""
    value = node.get("item_id")
    for prop in as_list(node.get("additionalProperty")):
        if isinstance(prop, dict) and prop.get("name") == "item_id":
            value = prop.get("value")
    value = str(value if value is not None else "")
    return value if is_embed_id(value) else ""


def json_ld_nodes(soup):
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except ValueError:
            continue
        yield from (node for node in as_list(data) if isinstance(node, dict))


def release_candidates(soup):
    """the release a page redirected to: an album by its json-ld, any by its page properties"""
    found = []
    for node in json_ld_nodes(soup):
        if "MusicAlbum" in as_list(node.get("@type")):
            found += [("album", item_id_of(release)) for release in as_list(node.get("albumRelease"))]
    meta = soup.find("meta", attrs={"name": "bc-page-properties"})
    try:
        properties = json.loads(meta.get("content", "")) if meta else {}
    except ValueError:
        properties = {}
    if isinstance(properties, dict) and properties.get("item_type") in PAGE_KINDS:
        found.append((PAGE_KINDS[properties["item_type"]], str(properties.get("item_id") or properties.get("id") or "")))
    return found


def grid_candidates(soup):
    """music tiles in page order; merchandise (and any other prefix) is skipped"""
    tiles = (TILE_RE.fullmatch(li["data-item-id"]) for li in soup.select("li[data-item-id]"))
    return [(tile.group(1), tile.group(2)) for tile in tiles if tile]


def find_candidates(html):
    """[(kind, id)]: the music releases a page offers, in its order, without repeats"""
    soup = BeautifulSoup(html, "html.parser")
    found = []
    for kind, embed_id in release_candidates(soup) + grid_candidates(soup):
        if is_embed_id(embed_id) and (kind, embed_id) not in found:
            found.append((kind, embed_id))
    return found


def fetch(session, url):
    """
    (problem, html, final url): the page, or why not: "blocked" (robots.txt, or 403, 406 or
    429), "gone" (404 or 410) or "failed" (anything else, and a redirect off bandcamp, which
    is never followed)
    """
    for _ in range(MAX_REDIRECTS + 1):
        if not robots_allows(session, url):
            return "blocked", "", url
        try:
            r = session.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=False)
        except requests.RequestException:
            return "failed", "", url
        if r.status_code in (301, 302, 303, 307, 308):
            url = urljoin(url, r.headers.get("Location") or "")
            if not is_bandcamp_url(url):
                return "failed", "", url
            continue
        if r.status_code in (403, 406, 429):
            return "blocked", "", url
        if r.status_code in (404, 410):
            return "gone", "", url
        if r.status_code != 200:
            return "failed", "", url
        return "", r.text, url
    return "failed", "", url


def player_available(session, kind, embed_id):
    """(problem, whether the player can play the release): its page, requested once"""
    problem, html, _ = fetch(session, bandcamp_player_url(kind, embed_id))
    if problem == "gone":
        return "", False
    if problem:
        return problem, False
    return "", is_playable(html)


def is_playable(html):
    """whether a player page's track data has a streamable track, in a release not withdrawn"""
    element = BeautifulSoup(html, "html.parser").find(attrs={PLAYER_DATA_ATTRIBUTE: True})
    if element is None:
        return False
    try:
        data = json.loads(element[PLAYER_DATA_ATTRIBUTE])
    except ValueError:
        return False
    if not isinstance(data, dict) or data.get("killed") or data.get("album_private") or data.get("subscriber_only"):
        return False
    tracks = data.get("tracks")
    return isinstance(tracks, list) and any(isinstance(track, dict) and track.get("file") for track in tracks)


def lookup(session, url):
    """the player of the act whose bandcamp page is url, as a Result"""
    problem, html, landed = fetch(session, url)
    if problem:
        return Result(Status(problem), why=problem)
    candidates = find_candidates(html)
    if not candidates:
        parts = urlsplit(landed)
        problem, html, _ = fetch(session, f"{parts.scheme}://{parts.netloc}/music")
        if problem and problem != "gone":
            return Result(Status(problem), why=problem)
        candidates = find_candidates(html)
    if not candidates:
        return Result(Status.UNREADABLE, why="no music release on the page")
    for kind, embed_id in candidates[:MAX_PLAYERS_TRIED]:
        problem, playable = player_available(session, kind, embed_id)
        if problem:
            return Result(Status(problem), why=problem)
        if playable:
            return Result(Status.FOUND, kind, embed_id)
    return Result(Status.NO_PLAYABLE, why="no release the player can play")


def keeps_found_player(record):
    """whether the record's found player is worth keeping: read from its current address"""
    return (
        record.bandcamp_embed_status == Status.FOUND
        and record.bandcamp_embed_kind != ""
        and record.bandcamp_embed_id != ""
        and record.bandcamp_embed_for == record.bandcamp_url
    )


def due(record, now, refresh=False):
    """
    whether to look the record up: it has an address, no decline and no editor's player, and
    its address was never looked up or has changed (recorded on every outcome), or its last
    look-up is old: a year for a found player, 90 days for the rest
    """
    if not record.bandcamp_url or record.bandcamp_embed_status == Status.DECLINED or record.bandcamp_player_by_editor:
        return False
    if refresh or record.bandcamp_embed_for != record.bandcamp_url or record.bandcamp_embed_checked_at is None:
        return True
    wait = REFRESH_FOUND_AFTER if record.bandcamp_embed_status == Status.FOUND else RETRY_OTHERS_AFTER
    return record.bandcamp_embed_checked_at < now - wait


def apply(record, result, now):
    """
    the fields to save for a look-up's result. a found player is saved; a failure leaves a
    player already found at the current address as it is (only the time moves), and
    otherwise records the failure's status, clearing a stale kind and id
    """
    if result.status == Status.FOUND:
        return {
            "bandcamp_embed_kind": result.kind,
            "bandcamp_embed_id": result.embed_id,
            "bandcamp_embed_status": Status.FOUND,
            "bandcamp_embed_for": record.bandcamp_url,
            "bandcamp_embed_checked_at": now,
        }
    if keeps_found_player(record):
        return {"bandcamp_embed_checked_at": now}
    return {
        "bandcamp_embed_kind": "",
        "bandcamp_embed_id": "",
        "bandcamp_embed_status": result.status,
        "bandcamp_embed_for": record.bandcamp_url,
        "bandcamp_embed_checked_at": now,
    }
