#!/usr/bin/env bash
# builds the site on the host (render runs this as its build command).
# exit on error
set -o errexit

pip install -r requirements.txt

# the tests run in github actions (.github/workflows/django.yml), and render
# only deploys a commit once they pass -- so they don't run here, where they
# would need to create a test database on the production postgres server.
# migrations run as render's pre-deploy command, after a successful build.
python manage.py compilescss
python manage.py collectstatic --no-input
