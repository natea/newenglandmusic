#!/usr/bin/env bash
# the daily scheduled job (render.yaml's newenglandmusic-daily; see PRODUCTION.md): syncs
# the venue sheet, looks up new venues on google places, refreshes coordinates before
# google's 30 days run out, then fetches every venue's events.
source "$(dirname "$0")/steps.sh"

step python manage.py sync_venues_from_gsheets
step python manage.py lookup_venue_places
step python manage.py lookup_venue_places --refresh-stale
step python manage.py fetch_events --all
finish
