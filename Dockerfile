# the site as a container, for pull request previews on cloud run (preview-environments).
# production doesn't use this: render builds with bin/build.sh. keep the python version,
# the build steps and the start command the same as render.yaml's
FROM python:3.11.14-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /code

# docker will not re-pip install if requirements.txt doesn't change
COPY requirements.txt /code/requirements.txt
RUN pip install -r requirements.txt

COPY . /code

# compiling the css and collecting the static files read the settings, but no database and
# no secret: these placeholders only let the settings load
RUN DJANGO_SETTINGS_MODULE=nycnoise.settings.preview \
    DJANGO_SECRET_KEY=build-only \
    DATABASE_URL=postgres://build:build@localhost/build \
    RC_DEVELOPER_INTERNAL_TOKEN=build-only \
    PROD_INTERNAL_API_SERVER=https://preview.invalid/ \
    PYINSTRUMENT_ENABLE=false \
    DEBUG_TOOLBAR_ENABLE=false \
    ENABLE_EMAILING_JESSICA_ON_EVENT_SUBMISSION=False \
    sh -c "python manage.py compilescss && python manage.py collectstatic --no-input"

# gunicorn listens on $PORT, which cloud run sets, as render does
CMD ["gunicorn", "--access-logformat", "%(h)s %(l)s %(t)s \"%(r)s\" %(s)s %(b)s \"%(f)s\" \"%(a)s\" reqtime: %(M)s ms", "nycnoise.wsgi:application"]
