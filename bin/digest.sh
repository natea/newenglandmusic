#!/usr/bin/env bash
# the weekly email job (render.yaml's newenglandmusic-digest; see PRODUCTION.md): sends each
# confirmed subscriber the week's matching shows, and deletes old unconfirmed sign-ups.
# it needs the web service's SITE_URL, sender address and mail credentials, and fails
# loudly, naming what's missing, when they aren't set.
source "$(dirname "$0")/steps.sh"

step python manage.py send_weekly_digests
finish
