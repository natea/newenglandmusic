"""
the youtube data api v3, for confirming which youtube channel or video is an artist's own
(match_youtube_artists), for the listing's youtube play buttons.

it needs YOUTUBE_API_KEY, a google cloud key restricted to youtube data api v3 (the only
google api to enable: see PRODUCTION.md). the key goes only in the X-goog-api-key header of
requests made here on the server, never in a url, page, log or error message.

the free quota is 10,000 units a day: a search costs 100, and a videos or channels lookup
costs 1 for up to 50 ids. YOUTUBE_PREVIEWS ("true") separately decides whether the listing
shows the buttons, so matches can be reviewed in the admin first.
"""

import os
import re
import time

import requests

API_URL = "https://www.googleapis.com/youtube/v3/"
MAX_TRIES = 3
TIMEOUT_SECONDS = 20
SEARCH_LIMIT = 10
# a videos or channels lookup takes at most this many ids, for one unit
IDS_PER_LOOKUP = 50
QUOTA_REASONS = {"quotaExceeded", "dailyLimitExceeded"}
CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
VIDEO_ID_RE = re.compile(r"^[\w-]{11}$")
CHANNEL_URL_RE = re.compile(r"^https?://(?:www\.|m\.)?youtube\.com/channel/(UC[\w-]{22})(?:[/?#].*)?$")
VIDEO_URL_RES = [
    re.compile(r"^https?://(?:www\.|m\.|music\.)?youtube\.com/watch\?(?:.*&)?v=([\w-]{11})(?:[&#].*)?$"),
    re.compile(r"^https?://youtu\.be/([\w-]{11})(?:[/?#].*)?$"),
    re.compile(r"^https?://(?:www\.)?youtube(?:-nocookie)?\.com/(?:embed|shorts)/([\w-]{11})(?:[/?#].*)?$"),
]


class YouTubeError(Exception):
    pass


class YouTubeQuotaExceeded(YouTubeError):
    """the day's quota is spent: no request is worth making until it resets"""


class YouTubeKeyRejected(YouTubeError):
    """google refused the key: it's wrong, its api isn't enabled, or its restrictions block us"""


def api_key():
    return os.environ.get("YOUTUBE_API_KEY") or None


def previews_enabled():
    """whether the listing shows youtube buttons"""
    return os.environ.get("YOUTUBE_PREVIEWS", "").lower() == "true"


def parse_link(text):
    """("channel", id) or ("video", id) for a youtube channel or video url, or None"""
    text = (text or "").strip()
    match = CHANNEL_URL_RE.match(text)
    if match:
        return "channel", match.group(1)
    for pattern in VIDEO_URL_RES:
        match = pattern.match(text)
        if match:
            return "video", match.group(1)
    return None


def uploads_playlist(channel_id):
    """a channel's uploads playlist: its id with "UC" made "UU" """
    return "UU" + channel_id[2:]


def error_reasons(response):
    """google's reasons for a failed request ("quotaExceeded"...), without anything we sent"""
    try:
        errors = (response.json().get("error") or {}).get("errors") or []
    except (ValueError, AttributeError):
        return []
    return [str(error.get("reason")) for error in errors if error and error.get("reason")]


class YouTubeClient:
    def __init__(self, key, session=None, sleep=time.sleep):
        self.key = key
        self.session = session or requests.Session()
        self.sleep = sleep
        self.units = 0

    def get(self, path, cost, **params):
        attempt = 0
        while True:
            try:
                response = self.session.get(
                    API_URL + path, params=params, headers={"X-goog-api-key": self.key}, timeout=TIMEOUT_SECONDS
                )
            except requests.RequestException as e:
                raise YouTubeError(f"{path}: {type(e).__name__}")
            self.units += cost
            if response.status_code == 200:
                return response.json()
            reasons = error_reasons(response)
            if response.status_code == 403 and QUOTA_REASONS & set(reasons):
                raise YouTubeQuotaExceeded(f"{path}: youtube's daily quota is spent ({', '.join(reasons)})")
            if response.status_code == 403 or (response.status_code == 400 and "keyInvalid" in reasons):
                # a referrer-restricted key gets 403 "forbidden" from a server, which sends
                # no referrer (2026-10-28): its application restriction must allow servers
                raise YouTubeKeyRejected(
                    f"{path}: HTTP {response.status_code} {', '.join(reasons)} -- google refused YOUTUBE_API_KEY; "
                    "check that YouTube Data API v3 is enabled for it, and that its application "
                    "restriction is None or the server's IP addresses, not websites"
                )
            if response.status_code != 429 and response.status_code < 500:
                raise YouTubeError(f"{path}: HTTP {response.status_code} {', '.join(reasons)}".strip())
            attempt += 1
            if attempt >= MAX_TRIES:
                raise YouTubeError(f"{path}: HTTP {response.status_code} after {MAX_TRIES} tries")
            self.sleep(2 ** (attempt - 1))

    def search_videos(self, query):
        """the video ids a search finds, best first"""
        data = self.get("search", 100, part="snippet", q=query, type="video", maxResults=SEARCH_LIMIT)
        return [
            item["id"]["videoId"]
            for item in data.get("items") or []
            if (item.get("id") or {}).get("videoId")
        ]

    def videos(self, ids):
        """{video id: {"channel_id", "channel_title", "title", "description", "embeddable"}}"""
        found = {}
        ids = list(ids)
        for start in range(0, len(ids), IDS_PER_LOOKUP):
            data = self.get("videos", 1, part="snippet,status", id=",".join(ids[start : start + IDS_PER_LOOKUP]))
            for item in data.get("items") or []:
                snippet, status = item.get("snippet") or {}, item.get("status") or {}
                found[item["id"]] = {
                    "channel_id": snippet.get("channelId", ""),
                    "channel_title": snippet.get("channelTitle", ""),
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "embeddable": bool(status.get("embeddable")),
                }
        return found

    def channels(self, ids):
        """the ids of these channels that exist"""
        found = set()
        ids = list(ids)
        for start in range(0, len(ids), IDS_PER_LOOKUP):
            data = self.get("channels", 1, part="id", id=",".join(ids[start : start + IDS_PER_LOOKUP]))
            found |= {item["id"] for item in data.get("items") or [] if item.get("id")}
        return found


def client():
    """a client with the environment's key; call only when api_key() is set"""
    return YouTubeClient(api_key())
