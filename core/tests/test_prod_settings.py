import json
import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# reads the production settings in a fresh interpreter, since django's
# settings are already configured (with the test settings) in this one
READ_PROD_SETTINGS = """
import json
from nycnoise.settings import prod
print(json.dumps({
    "debug": prod.DEBUG,
    "allowed_hosts": prod.ALLOWED_HOSTS,
    "proxy_header": prod.SECURE_PROXY_SSL_HEADER,
    "secure_cookies": [prod.SESSION_COOKIE_SECURE, prod.CSRF_COOKIE_SECURE],
    "site_url": prod.SITE_URL,
}))
"""


class ProdSettingsTestCase(SimpleTestCase):
    def prod_settings(self, allowed_hosts="newenglandmusic.example", **env):
        # start from a host that isn't render, whatever this machine's .env says
        render_vars = ("RENDER_EXTERNAL_HOSTNAME", "RENDER_EXTERNAL_URL", "SITE_URL")
        base_env = {key: value for key, value in os.environ.items() if key not in render_vars}
        base_env["SITE_URL"] = ""
        result = subprocess.run(
            [sys.executable, "-c", READ_PROD_SETTINGS],
            capture_output=True,
            text=True,
            check=True,
            cwd=PROJECT_ROOT,
            env={**base_env, "ALLOWED_HOSTS": allowed_hosts, **env},
        )
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_renders_hostname_is_allowed(self):
        prod = self.prod_settings(RENDER_EXTERNAL_HOSTNAME="newenglandmusic.onrender.com")
        self.assertEqual(
            prod["allowed_hosts"], ["newenglandmusic.example", "newenglandmusic.onrender.com"]
        )

    def test_without_render_only_the_configured_hosts(self):
        prod = self.prod_settings()
        self.assertEqual(prod["allowed_hosts"], ["newenglandmusic.example"])

    def test_https_behind_the_proxy(self):
        prod = self.prod_settings()
        self.assertFalse(prod["debug"])
        self.assertEqual(prod["proxy_header"], ["HTTP_X_FORWARDED_PROTO", "https"])
        self.assertEqual(prod["secure_cookies"], [True, True])

    def test_blank_allowed_hosts_on_render(self):
        prod = self.prod_settings(
            allowed_hosts="", RENDER_EXTERNAL_HOSTNAME="newenglandmusic.onrender.com"
        )
        self.assertEqual(prod["allowed_hosts"], ["newenglandmusic.onrender.com"])

    def test_site_url_falls_back_to_the_render_address(self):
        prod = self.prod_settings(RENDER_EXTERNAL_URL="https://newenglandmusic.onrender.com")
        self.assertEqual(prod["site_url"], "https://newenglandmusic.onrender.com")
        prod = self.prod_settings(
            SITE_URL="https://newenglandmusic.example/",
            RENDER_EXTERNAL_URL="https://newenglandmusic.onrender.com",
        )
        self.assertEqual(prod["site_url"], "https://newenglandmusic.example")
