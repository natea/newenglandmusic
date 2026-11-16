#!/usr/bin/env bash
# the weekly scheduled job (render.yaml's newenglandmusic-weekly; see PRODUCTION.md):
# re-checks how each venue's events can be fetched, then links venues to ticketmaster, to
# their eventbrite organizers and to seatgeek, and finds venues' neighborhoods. weekly,
# because the check crawls every venue's site.
# not here, and run by hand (see PRODUCTION.md): find_bandcamp_embeds, as bandcamp challenges
# requests from render's servers, and read_artist_link_hubs, as the hubs' robots.txt forbids it
source "$(dirname "$0")/steps.sh"

# 8 crawl workers, not 16, to stay inside the job's 512mb
step python manage.py check_event_sources --workers 8
step python manage.py match_ticketmaster_venues
step python manage.py match_eventbrite_organizers
step python manage.py match_seatgeek_venues
# venues' neighborhoods from openstreetmap: only venues never looked up, or a year ago
step python manage.py lookup_venue_neighborhoods
finish
