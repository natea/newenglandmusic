#!/usr/bin/env bash
# builds the scheduled jobs (render runs this as their build command). they serve no
# pages, so they need no static files, and only the web service migrates, so two builds
# never migrate at once.
set -o errexit

pip install -r requirements.txt
