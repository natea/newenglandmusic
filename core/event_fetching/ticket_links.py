"""
finds where a venue sells its tickets, from the links on its own events page: each show's
page on etix or axs, and the venue's list of shows there. seatgeek events link to these
(see fetch_events), since seatgeek's api never says where a show is sold.

only the venue's own page is read, never etix's or axs's, which refuse crawlers.
"""

import re
import unicodedata

from bs4 import BeautifulSoup

# e.g. https://www.etix.com/ticket/p/96934398/as-i-lay-dying-new-haven-toads-place-of-new-haven
# and https://www.axs.com/events/1329972/hiss-golden-messenger-tickets
SHOW_LINK_RE = re.compile(
    r"^https?://(?:www\.)?(?:etix\.com/ticket/p|axs\.com/events)/\d+/(?P<slug>[a-z0-9-]+)",
    re.IGNORECASE,
)
# e.g. https://www.etix.com/ticket/v/677 and https://www.axs.com/venues/124878/the-sinclair-cambridge-tickets
VENUE_LINK_RE = re.compile(
    r"^https?://(?:www\.)?(?:etix\.com/ticket/v/\d+|axs\.com/venues/\d+(?:/[a-z0-9-]+)?)",
    re.IGNORECASE,
)
# shorter titles ("XO") would match too many shows
MIN_TITLE_LENGTH = 3


def slugify(text):
    """lowercase words joined by hyphens, without accents or apostrophes, as etix and axs do"""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"['’.]", "", text)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def find_ticket_links(html):
    """
    returns (show links, venue links) on a page: {url: slug} for each show's page, and the
    venue pages, without query strings or repeats
    """
    shows, venues = {}, []
    for anchor in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        href = anchor["href"].split("#")[0].split("?")[0]
        if match := SHOW_LINK_RE.match(href):
            shows.setdefault(match.group(0), match.group("slug").lower())
        elif match := VENUE_LINK_RE.match(href):
            if match.group(0) not in venues:
                venues.append(match.group(0))
    return shows, venues


def match_show(show_links, title, headliner=""):
    """
    the one show link whose slug starts with the event's title, or else its headliner's
    name. etix drops punctuation without a hyphen ("Eggy: The Final Tour" is
    "eggythe-final-tour"), so a prefix is enough. a title several links share, like a
    weekly dance party, matches none
    """
    for name in (title, headliner):
        prefix = slugify(name)
        if len(prefix) < MIN_TITLE_LENGTH:
            continue
        found = [url for url, slug in show_links.items() if slug.startswith(prefix)]
        if len(found) == 1:
            return found[0]
        if found:
            return ""
    return ""
