"""
settings of a pull request's preview (preview-environments): production's, cut off from the
outside. a preview answers at its own run.app address, on its own copy of a cleaned snapshot
of the live data.
"""

from .prod import *

# marks a preview: the data-export endpoint answers 404 (core/views/internal_db_dump.py)
PREVIEW = True

# a preview's address isn't known before its first deploy, and it never answers for the site's
ALLOWED_HOSTS = [".run.app"]
CANONICAL_HOST = ""

# no sender, so every email is refused (core/digest_mail.py), whatever the environment says
DEFAULT_FROM_EMAIL = ""

# neon suspends an idle database, so a kept connection would fail on the next request
DATABASES["default"]["CONN_MAX_AGE"] = 0

# first, above whitenoise, so static files ask not to be indexed too
MIDDLEWARE = ["core.middleware.NoIndexMiddleware", *MIDDLEWARE]
