"""Access the optional studio package with a clear error when it is absent.

``django_control_components.studio`` ships as a separate distribution
(``django-control-components-studio``). Panels that call ``.studio()`` or
``.dynamic()`` need it; without it the bare ``ModuleNotFoundError`` is replaced
with an actionable hint.
"""

from __future__ import annotations

import importlib
from types import ModuleType

_HINT = 'pip install "django-control-components[studio]"'


def require_studio(submodule: str) -> ModuleType:
    """Import ``django_control_components.studio.<submodule>`` or raise
    :class:`~django.core.exceptions.ImproperlyConfigured` with an install hint."""
    try:
        return importlib.import_module(f"django_control_components.studio.{submodule}")
    except ModuleNotFoundError as exc:
        if (exc.name or "").startswith("django_control_components.studio"):
            from django.core.exceptions import ImproperlyConfigured

            raise ImproperlyConfigured(
                "Panel.studio()/.dynamic() requires the studio package. " + _HINT
            ) from exc
        raise
