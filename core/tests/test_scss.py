from pathlib import Path

import sass
from django.test import SimpleTestCase

SCSS = Path(__file__).resolve().parent.parent / "static" / "core" / "scss"


class ScssCompilesTestCase(SimpleTestCase):
    """tests render templates without compiling stylesheets, so a sass error only showed
    as a 500 in the browser (band.scss, 2026-10-29); each top-level sheet compiles here"""

    def test_every_page_stylesheet_compiles(self):
        for name in ("core.scss", "band.scss"):
            with self.subTest(sheet=name):
                css = sass.compile(filename=str(SCSS / name), include_paths=[str(SCSS)])
                self.assertTrue(css.strip())
