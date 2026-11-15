import os

from .base import *

DEBUG = False

# render serves each service at <name>.onrender.com and says so in this
# variable, so the site works there before (and alongside) a custom domain
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])

# the site's address (see PRODUCTION.md), accepted from the first deploy, before DNS points
# here, so the switch has no moment when django refuses the new hosts
for host in ("stagehopper.app", "www.stagehopper.app"):
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

# the host's proxy ends https and forwards plain http: without this, django
# thinks every request is insecure and refuses admin logins (csrf origin check)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# default logging doesn't log to console with DEBUG=False
# see https://github.com/django/django/blob/main/django/utils/log.py
# override i.e. always log to console
LOGGING["handlers"]["console"] = {
    "class": "logging.StreamHandler",
}
