"""Download the pinned htmx / Alpine / focus assets into a project static dir.

Run once (and after every version bump) so ``DCC["VENDOR_ASSETS"] = True`` can
serve them from the same origin — no CDN, no SRI needed.

    python manage.py dcc_vendor_assets --dest myproject/static/dcc/vendor/
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from ...htmx import HTMX_SRC
from ...templatetags.dcc_tags import _ALPINE_FOCUS_SRC, _ALPINE_SRC, VENDOR_NAMES

_SOURCES = {
    VENDOR_NAMES["htmx"]: HTMX_SRC,
    VENDOR_NAMES[_ALPINE_SRC]: _ALPINE_SRC,
    VENDOR_NAMES[_ALPINE_FOCUS_SRC]: _ALPINE_FOCUS_SRC,
}


class Command(BaseCommand):
    help = "Fetch the pinned htmx/Alpine/focus files for DCC['VENDOR_ASSETS']."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dest",
            required=True,
            help="Directory to write the files into (a project static path).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dest = Path(options["dest"])
        dest.mkdir(parents=True, exist_ok=True)
        for name, url in _SOURCES.items():
            try:
                with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - pinned https
                    body = response.read()
            except OSError as exc:
                raise CommandError(f"failed to fetch {url}: {exc}") from exc
            (dest / name).write_bytes(body)
            self.stdout.write(self.style.SUCCESS(f"wrote {dest / name} ({len(body)} bytes)"))
        self.stdout.write("Set DCC['VENDOR_ASSETS'] = True to serve these.")
