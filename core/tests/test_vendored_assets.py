"""
vendored libraries' files, as production's static storage reads them: whitenoise's manifest
storage follows every sourceMappingURL in a .css or .js file and fails the build (collectstatic)
when the file it names is missing, which development's static serving never notices.
"""

import re
from pathlib import Path

from django.test import SimpleTestCase

VENDOR = Path(__file__).resolve().parents[1] / "static" / "core" / "vendor"
SOURCE_MAP = re.compile(r"sourceMappingURL=([^\s*]+)")


class VendoredAssetsTestCase(SimpleTestCase):
    def test_every_source_map_is_there(self):
        files = [path for path in VENDOR.rglob("*") if path.suffix in (".css", ".js")]
        self.assertTrue(files)
        for path in files:
            for name in SOURCE_MAP.findall(path.read_text(errors="ignore")):
                self.assertTrue((path.parent / name).exists(), f"{path.name} names {name}, which isn't vendored")

    def test_each_library_keeps_its_licence(self):
        for version in (path for path in VENDOR.glob("*/*") if path.is_dir()):
            self.assertTrue(list(version.glob("LICENSE*")), f"{version} has no licence")
