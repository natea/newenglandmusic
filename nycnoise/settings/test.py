import sys

from .base import *

# like on dev
DEBUG = True

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # https://stackoverflow.com/a/76117900
        # "disables the caching behavior for the tests, for static files to load properly"
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"
    },
}

# this is used to quelch a
# "UserWarning: No directory at: .../staticfiles/" warning
WHITENOISE_AUTOREFRESH = True

# tests never send email
EMAIL_ON_EVENT_SUBMISSION = False

# every test renders /bands afresh, from its own data
ACT_INDEX_CACHE_SECONDS = 0
