"""Canonical home moved to ``core/visibility.py`` (a ``Layout`` container needs
the same DSL as a ``Field``, and ``core`` is the shared ancestor). Re-exported
here for one release."""

from __future__ import annotations

from ..core.visibility import VisibilityRule

__all__ = ["VisibilityRule"]
