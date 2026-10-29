"""
an act's english wikipedia article, for its introduction (enrich_artists_from_musicbrainz):
wikidata gives the article's title for the act's wikidata id, and wikipedia's rest api its
summary, whose plain-text "extract" is the article's opening paragraph.

wikipedia's text is cc by-sa 4.0: it's kept word for word (changing it would make ours a
derivative to license and mark as modified), and credited wherever it's shown with a link
to the article and the licence. summaries' images aren't kept, as each has its own licence.
both are free and keyless; wikimedia asks for a user agent with contact details
(core/user_agent.py), and requests here are paced.
"""

import re
import time
from urllib.parse import quote

import requests

from core.user_agent import user_agent

WIKIDATA_URL = "https://www.wikidata.org/w/api.php"
SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
TIMEOUT_SECONDS = 20
SECONDS_BETWEEN_REQUESTS = 1.0
WIKIDATA_ID_RE = re.compile(r"^Q\d+$")


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

    def article_title(self, wikidata_id):
        """the english wikipedia article's title for a wikidata item, or None"""
        if not WIKIDATA_ID_RE.match(wikidata_id or ""):
            return None
        data = self.get(
            WIKIDATA_URL, "wikidata", action="wbgetentities", ids=wikidata_id, props="sitelinks",
            sitefilter="enwiki", format="json",
        ) or {}
        sitelinks = ((data.get("entities") or {}).get(wikidata_id) or {}).get("sitelinks") or {}
        return (sitelinks.get("enwiki") or {}).get("title") or None

    def introduction(self, wikidata_id):
        """
        {"extract", "url", "revision"} for the wikidata item's english article, or None when
        it has none, or the summary isn't an ordinary article of that item
        """
        title = self.article_title(wikidata_id)
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
