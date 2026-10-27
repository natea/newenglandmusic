#!/usr/bin/env bash
# the daily scheduled job (render.yaml's newenglandmusic-daily; see PRODUCTION.md): syncs
# the venue sheet, looks up new venues on google places, refreshes coordinates before
# google's 30 days run out, fetches every venue's events, then links the artists on
# upcoming events to spotify and apple music for the listing's play buttons.
source "$(dirname "$0")/steps.sh"

step python manage.py sync_venues_from_gsheets
step python manage.py lookup_venue_places
step python manage.py lookup_venue_places --refresh-stale
step python manage.py fetch_events --all
# daily, so a first run's backlog clears itself: when spotify blocks the app (development
# mode gets little), the run stops and keeps what it found, and tomorrow's carries on.
# --limit keeps each morning's searches well under the burst that got a day-long block
step python manage.py match_spotify_artists --limit 1000
# does nothing until the musickit key is set (see PRODUCTION.md)
step python manage.py match_apple_music_artists --limit 1000
finish
