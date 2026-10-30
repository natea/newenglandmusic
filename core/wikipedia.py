"""
an act's english wikipedia article, for its introduction (enrich_artists_from_musicbrainz):
wikidata gives the article's title for the act's wikidata id, and wikipedia's rest api its
summary, whose plain-text "extract" is the article's opening paragraph. the same wikidata
request gives its photo (a wikimedia commons file), instagram and youtube; commons gives the
photo's licence and author, and only a free licence is kept, as a credit, never the image.

wikipedia's text is cc by-sa 4.0: it's kept word for word (changing it would make ours a
derivative to license and mark as modified), and credited wherever it's shown with a link
to the article and the licence. summaries' images aren't kept, as each has its own licence.
both are free and keyless; wikimedia asks for a user agent with contact details
(core/user_agent.py), and requests here are paced.
"""

import re
import time
from html import unescape
from urllib.parse import quote

import requests

from django.utils.html import strip_tags

from core.user_agent import user_agent

WIKIDATA_URL = "https://www.wikidata.org/w/api.php"
COMMONS_URL = "https://commons.wikimedia.org/w/api.php"
SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
TIMEOUT_SECONDS = 20
SECONDS_BETWEEN_REQUESTS = 1.0
WIKIDATA_ID_RE = re.compile(r"^Q\d+$")
# wikidata properties: image, instagram username, youtube channel id
IMAGE, INSTAGRAM, YOUTUBE = "P18", "P2003", "P2397"
INSTAGRAM_NAME_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
YOUTUBE_CHANNEL_RE = re.compile(r"^UC[\w-]{22}$")
# the free licences a photo may carry here, by commons' short name: public domain, cc0,
# cc by and cc by-sa ("CC BY-SA 3.0"), never a non-commercial or no-derivatives one
FREE_LICENSE_RE = re.compile(r"^(public domain|cc0|cc by(-sa)? \d)", re.IGNORECASE)


def commons_thumbnail(file_name, width):
    """commons' own thumbnail of a file, which wikimedia serves for embedding"""
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(file_name.replace(' ', '_'))}?width={int(width)}"


def commons_file_page(file_name):
    return f"https://commons.wikimedia.org/wiki/File:{quote(file_name.replace(' ', '_'))}"


class WikipediaError(Exception):
    pass


class Wikipedia:
    def __init__(self, session=None, sleep=time.sleep, clock=time.monotonic):
        self.session = session or requests.Session()
        self.sleep = sleep
        self.clock = clock
        self.last_request_at = None

    def get(self, url, what, **params):
        """the json answer, or None for 404"""
        if self.last_request_at is not None:
            wait = self.last_request_at + SECONDS_BETWEEN_REQUESTS - self.clock()
            if wait > 0:
                self.sleep(wait)
        self.last_request_at = self.clock()
        try:
            response = self.session.get(
                url, params=params or None, headers={"User-Agent": user_agent()}, timeout=TIMEOUT_SECONDS
            )
        except requests.RequestException as e:
            raise WikipediaError(f"{what}: {type(e).__name__}")
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise WikipediaError(f"{what}: HTTP {response.status_code}")
        return response.json()

    def entity(self, wikidata_id):
        """
        {"title", "image", "instagram", "youtube"} for a wikidata item: its english
        wikipedia article's title, its image's commons file name, and its instagram and
        youtube links, each "" when it has none. None for an id that isn't one or no item
        """
        if not WIKIDATA_ID_RE.match(wikidata_id or ""):
            return None
        data = self.get(
            WIKIDATA_URL, "wikidata", action="wbgetentities", ids=wikidata_id, props="claims|sitelinks",
            sitefilter="enwiki", format="json",
        ) or {}
        item = (data.get("entities") or {}).get(wikidata_id) or {}
        if not item or "missing" in item:
            return None
        claims = item.get("claims") or {}

        def first(prop):
            for claim in claims.get(prop) or []:
                value = ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")
                if isinstance(value, str) and value.strip() and claim.get("rank") != "deprecated":
                    return value.strip()
            return ""

        instagram, youtube = first(INSTAGRAM), first(YOUTUBE)
        return {
            "title": ((item.get("sitelinks") or {}).get("enwiki") or {}).get("title") or "",
            "image": first(IMAGE),
            "instagram": f"https://www.instagram.com/{instagram}/" if INSTAGRAM_NAME_RE.match(instagram) else "",
            "youtube": f"https://www.youtube.com/channel/{youtube}" if YOUTUBE_CHANNEL_RE.match(youtube) else "",
        }

    def article_title(self, wikidata_id):
        """the english wikipedia article's title for a wikidata item, or None"""
        return ((self.entity(wikidata_id) or {}).get("title")) or None

    def photo(self, file_name):
        """
        {"file", "author", "license", "license_url"} for a commons file under a free licence
        (FREE_LICENSE_RE), or None: the credit the page shows under commons' own thumbnail
        """
        if not file_name or "/" in file_name:
            return None
        data = self.get(
            COMMONS_URL, "commons", action="query", titles=f"File:{file_name}", prop="imageinfo",
            iiprop="extmetadata", format="json",
        ) or {}
        pages = list(((data.get("query") or {}).get("pages") or {}).values())
        info = ((pages[0].get("imageinfo") or [{}])[0] if pages else {}) or {}
        meta = info.get("extmetadata") or {}

        def value(key):
            return unescape(strip_tags(str((meta.get(key) or {}).get("value") or ""))).strip()

        license = value("LicenseShortName")
        if not FREE_LICENSE_RE.match(license):
            return None
        url = value("LicenseUrl")
        return {
            "file": file_name,
            "author": " ".join(value("Artist").split())[:255] or "unknown",
            "license": license[:64],
            "license_url": ("https:" + url if url.startswith("//") else url)[:300],
        }

    def introduction(self, wikidata_id, entity=None):
        """
        {"extract", "url", "revision"} for the wikidata item's english article, or None when
        it has none, or the summary isn't an ordinary article of that item. entity: the
        item's entity() when the caller already asked for it
        """
        if entity is None:
            entity = self.entity(wikidata_id)
        title = (entity or {}).get("title")
        if not title:
            return None
        summary = self.get(SUMMARY_URL.format(title=quote(title.replace(" ", "_"), safe="")), "wikipedia")
        if not summary or summary.get("type") != "standard" or summary.get("wikibase_item") != wikidata_id:
            return None
        extract = (summary.get("extract") or "").strip()
        url = (((summary.get("content_urls") or {}).get("desktop") or {}).get("page")) or ""
        if not extract or not url:
            return None
        return {"extract": extract, "url": url, "revision": str(summary.get("revision") or "")}
