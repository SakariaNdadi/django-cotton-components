"""Grep-as-test guardrails. Cheap, and they catch regressions no unit test would."""

from __future__ import annotations

import pathlib

import django_cotton_components

ROOT = pathlib.Path(django_cotton_components.__file__).parent
TEMPLATES = ROOT / "templates"


def _template_files():
    return list(TEMPLATES.rglob("*.html"))


def test_no_literal_hx_attributes_in_templates():
    """Every hx-* must come from htmx.py so the htmx-4 migration is one file."""
    tokens = ("hx-get", "hx-post", "hx-put", "hx-patch", "hx-delete", "hx-target", "hx-swap")
    offenders = []
    for path in _template_files():
        text = path.read_text()
        for token in tokens:
            if token in text:
                offenders.append(f"{path.relative_to(ROOT)}: {token}")
    assert not offenders, offenders


def test_no_hand_rolled_buttons_outside_primitives():
    """Buttons come from the `ui` layer (or a cotton wrapper of it), not ad-hoc
    ``<button class="dcc-btn">`` per template. A handful of component-internal
    Alpine controls carry their own class and are exempt."""
    exempt = {
        "templates/cotton/dcc/button.html",
        "templates/cotton/dcc/modal.html",
        "templates/django_cotton_components/ui/button.html",
        "templates/django_cotton_components/ui/menu.html",
        "templates/django_cotton_components/ui/modal.html",
        # component-internal controls with their own class (not dcc-btn)
        "templates/django_cotton_components/controls/select.html",
        "templates/django_cotton_components/controls/password.html",
        "templates/django_cotton_components/layout/tabs.html",
        # client-side sort header toggle — bare button, no dcc-btn
        "templates/django_cotton_components/tables/_content.html",
    }
    offenders = []
    for path in _template_files():
        rel = str(path.relative_to(ROOT))
        if rel in exempt:
            continue
        if 'class="dcc-btn' in path.read_text():
            offenders.append(rel)
    assert not offenders, offenders


def test_no_django_interpolation_inside_alpine_data():
    """No {{ }} inside x-data='{ ... }' — that is the JS-injection footgun."""
    offenders = []
    for path in _template_files():
        for line in path.read_text().splitlines():
            if "x-data=" in line and "{{" in line and "}}" in line:
                # allow x-data="dccSelect('{{ id }}-data')" style single-arg factory calls
                if "dcc" in line and line.count("{{") == 1:
                    continue
                offenders.append(f"{path.relative_to(ROOT)}: {line.strip()}")
    assert not offenders, offenders


def test_mark_safe_only_at_reviewed_sites():
    allowed = {
        "core/attributes.py",
        "templatetags/dcc_tags.py",
        "schemas/schema.py",
        "schemas/layout.py",
        "tables/columns.py",  # .allow_html() — documented opt-in, escaping is default
        "icons/fontawesome.py",  # fixed markup + a setting-controlled asset URL
    }
    offenders = []
    for path in ROOT.rglob("*.py"):
        rel = str(path.relative_to(ROOT))
        if rel in allowed:
            continue
        text = path.read_text()
        if "mark_safe(" in text or "mark_safe (" in text:
            offenders.append(rel)
    assert not offenders, offenders
