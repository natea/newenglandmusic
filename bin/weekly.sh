#!/usr/bin/env bash
# the weekly scheduled job (render.yaml's newenglandmusic-weekly; see PRODUCTION.md):
# re-checks how each venue's events can be fetched, then links venues to ticketmaster, to
# their eventbrite organizers and to seatgeek, reads artists' link-hub pages, and last reads
# acts' bandcamp player ids from their own pages. weekly, because the check crawls every venue's site.
source "$(dirname "$0")/steps.sh"

# 8 crawl workers, not 16, to stay inside the job's 512mb
step python manage.py check_event_sources --workers 8
step python manage.py match_ticketmaster_venues
step python manage.py match_eventbrite_organizers
step python manage.py match_seatgeek_venues
# venues' neighborhoods from openstreetmap: only venues never looked up, or a year ago
step python manage.py lookup_venue_neighborhoods
# artists' and bands' link-hub pages (linktr.ee and its rivals), one request each, at most weekly
step python manage.py read_artist_link_hubs
# acts' bandcamp player ids, read from their own pages: last, so a link a hub just filled is looked up now
step python manage.py find_bandcamp_embeds
finish
