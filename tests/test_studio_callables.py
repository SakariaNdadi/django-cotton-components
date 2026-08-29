"""The @alias escape hatch: a spec references a predicate by alias, never path."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from django_control_components.studio.deserialize import build_infolist_from_spec
from tests.testapp.models import Article

pytestmark = pytest.mark.django_db


def _entry_spec(config):
    return {"entries": [{"type": "TextEntry", "name": "title", "config": config}]}


def _render(spec, record):
    from django.test import RequestFactory

    infolist = build_infolist_from_spec(Article, spec)
    return str(infolist.render(request=RequestFactory().get("/"), record=record))


def test_registered_alias_resolves_to_the_callable(settings, article):
    settings.DCC = {"STUDIO_CALLABLES": {"always": "tests.testapp.rules.always_true"}}
    assert "Analytical Engine" in _render(_entry_spec({"visible": "@always"}), article)


def test_hidden_by_alias_removes_the_entry(settings, article):
    settings.DCC = {"STUDIO_CALLABLES": {"never": "tests.testapp.rules.always_false"}}
    spec = {
        "entries": [
            {"type": "TextEntry", "name": "title", "config": {"visible": "@never"}},
            {"type": "TextEntry", "name": "slug"},
        ]
    }
    html = _render(spec, article)
    assert "analytical-engine" in html
    assert "Analytical Engine" not in html


def test_unregistered_alias_is_rejected(settings):
    settings.DCC = {"STUDIO_CALLABLES": {}}
    with pytest.raises(ValidationError):
        build_infolist_from_spec(Article, _entry_spec({"visible": "@mystery"}))


def test_a_bare_callable_value_is_still_rejected(settings):
    settings.DCC = {"STUDIO_CALLABLES": {"x": "tests.testapp.rules.always_true"}}
    with pytest.raises(ValidationError):
        build_infolist_from_spec(Article, _entry_spec({"visible": "os.system"}))


def test_state_still_cannot_be_aliased(settings):
    settings.DCC = {"STUDIO_CALLABLES": {"x": "tests.testapp.rules.always_true"}}
    with pytest.raises(ValidationError):
        build_infolist_from_spec(Article, _entry_spec({"state": "@x"}))
