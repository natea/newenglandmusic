"""
the shows a visitor has saved, kept in their browser as a cookie of event ids, newest first
(core/static/core/js/saved_shows.js writes it; the /saved page reads it, and rewrites it
without the shows that can no longer happen). nothing about the visitor is stored here.
"""

from urllib.parse import quote, unquote

COOKIE_NAME = "saved_shows"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60
# 300 ids of up to 5 digits is under 2kb, well inside a cookie's 4kb
MAX_SAVED = 300


def parse_saved(cookie):
    """the cookie's event ids, in order: positive whole numbers, without repeats"""
    ids = []
    # the browser writes the commas encoded ("12%2C7"), as cookie values may not hold them
    for part in unquote(cookie or "").split(","):
        part = part.strip()
        if part.isdigit() and int(part) > 0 and int(part) not in ids:
            ids.append(int(part))
    return ids[:MAX_SAVED]


def format_saved(ids):
    """the cookie value: commas encoded as the browser writes them, or django would quote
    and escape the value ("\"12\\0547\""), which the browser's script can't read"""
    return quote(",".join(str(event_id) for event_id in ids))


def toggle_saved(ids, event_id):
    """the ids with event_id removed if saved, or else added first, the oldest past the limit dropped"""
    if event_id in ids:
        return [saved for saved in ids if saved != event_id]
    return ([event_id] + ids)[:MAX_SAVED]
