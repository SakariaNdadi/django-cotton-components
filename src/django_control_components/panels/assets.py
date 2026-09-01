"""Front-end assets a widget needs on the page.

A widget declares the scripts/stylesheets its client renderer depends on. The
dashboard collects them across every widget, de-duplicates by URL, and emits each
one once in the page ``<head>``. Delivery is opt-in per widget - nothing is added
to ``{% dcc_assets %}``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Chart.js UMD build - the reference charting library. Pinned, from the same CDN
# as htmx and Alpine.
CHARTJS_SRC = "https://cdn.jsdelivr.net/npm/chart.js@4.4.6/dist/chart.umd.min.js"


@dataclass(frozen=True, slots=True)
class Asset:
    kind: Literal["script", "style"]
    url: str
