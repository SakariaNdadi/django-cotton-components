"""Optional third-party integrations."""

from __future__ import annotations

import importlib

import pytest


def test_allauth_module_guards_its_missing_dependency():
    try:
        import allauth  # noqa: F401
    except ImportError:
        from django.core.exceptions import ImproperlyConfigured

        with pytest.raises(ImproperlyConfigured):
            importlib.import_module("django_cotton_components.integrations.allauth")
    else:  # pragma: no cover - only when the extra is installed
        mod = importlib.import_module("django_cotton_components.integrations.allauth")
        assert hasattr(mod, "DCCAccountAdapter")


def test_library_imports_without_the_extra():
    importlib.import_module("django_cotton_components.panels")
    importlib.import_module("django_cotton_components.studio")
