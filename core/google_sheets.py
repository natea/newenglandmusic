"""
reads a google sheet's values with a google cloud service account, for servers where the
gog cli can't sign in (it needs a browser). the account's json key comes from the
GOOGLE_SERVICE_ACCOUNT_JSON environment variable, and the sheet must be shared with the
account's email address as a viewer. see PRODUCTION.md for the one-time setup.

errors name the tab and what to do, but never include the key or a token.
"""

import json
import os
from urllib.parse import quote

from django.core.management.base import CommandError
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
VALUES_URL = "https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{a1_range}"
TIMEOUT_SECONDS = 30
ENV_VAR = "GOOGLE_SERVICE_ACCOUNT_JSON"


def is_configured():
    return bool(os.environ.get(ENV_VAR, "").strip())


def load_key():
    try:
        info = json.loads(os.environ[ENV_VAR])
        if info.get("type") != "service_account" or not info.get("client_email"):
            raise ValueError
    except (KeyError, ValueError, AttributeError):
        # never echo the value: it's the private key
        raise CommandError(f"{ENV_VAR} isn't a valid service-account key") from None
    return info


def read_values(sheet_id, a1_range, tab):
    """the range's values (a list of rows), formatted as the sheet shows them, like gog's"""
    info = load_key()
    try:
        credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        response = AuthorizedSession(credentials).get(
            VALUES_URL.format(sheet_id=sheet_id, a1_range=quote(a1_range, safe="")),
            params={"valueRenderOption": "FORMATTED_VALUE"},
            timeout=TIMEOUT_SECONDS,
        )
    except (GoogleAuthError, ValueError):
        # a refresh error can carry the token response, so its message isn't passed on
        raise CommandError(f"couldn't sign in to google sheets with {ENV_VAR}") from None

    if response.status_code == 200:
        return response.json().get("values", [])
    try:
        message = (response.json().get("error") or {}).get("message", "")
    except ValueError:
        message = ""
    if response.status_code in (403, 404):
        raise CommandError(
            f"can't read tab {tab!r}: share the sheet with {info['client_email']} as a Viewer"
        )
    if response.status_code == 400 and "Unable to parse range" in message:
        raise CommandError(f"tab {tab!r} doesn't exist")
    raise CommandError(f"can't read tab {tab!r}: HTTP {response.status_code} {message[:200]}")
