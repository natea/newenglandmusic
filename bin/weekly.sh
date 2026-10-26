#!/usr/bin/env bash
# the weekly scheduled job (render.yaml's newenglandmusic-weekly; see PRODUCTION.md):
# re-checks how each venue's events can be fetched, then links venues to ticketmaster and
# to their eventbrite organizers. weekly, because the check crawls every venue's site.
source "$(dirname "$0")/steps.sh"

# 8 crawl workers, not 16, to stay inside the job's 512mb
step python manage.py check_event_sources --workers 8
step python manage.py match_ticketmaster_venues
step python manage.py match_eventbrite_organizers
finish
