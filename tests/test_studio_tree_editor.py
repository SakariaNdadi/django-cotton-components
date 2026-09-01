"""Phase 5: the block-tree editor.

The interactive editing lives in ``dcc-studio.js`` (``dccTree`` + the
``x-recurse`` directive) and is not unit-testable here; what this file locks
down is the server contract it depends on — the palette exposing each block's
slots, and a nested tree in the shape ``dccTree`` produces surviving a
save / hydrate round-trip.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from django.contrib.auth.models import Permission
from django.urls import include, path

from django_control_components.panels import Panel
from django_control_components.studio.models import Page
from django_control_components.studio.palette import palette

pytestmark = pytest.mark.django_db

panel = Panel("s").path("s").studio().auth(lambda r: True)
urlpatterns = [
    panel.mount(),
    path("studio/", include("django_control_components.studio.urls")),
]


@pytest.fixture
def urlconf(settings):
    settings.ROOT_URLCONF = __name__
    settings.LOGIN_URL = "/accounts/login/"


@pytest.fixture
def studio_user(django_user_model):
    user = django_user_model.objects.create_user("editor", password="x")
    user.user_permissions.add(Permission.objects.get(codename="use_studio"))
    return django_user_model.objects.get(pk=user.pk)


def test_palette_exposes_block_slots():
    blocks = {b["name"]: b for b in palette(None)["blocks"]}
    assert set(blocks["AppShell"]["slots"]) == {"topbar", "sidebar", "content", "footer"}
    assert blocks["Grid"]["slots"] == ["default"]
    assert blocks["Divider"]["slots"] == []


def test_js_ships_the_recurse_directive_and_tree_store():
    import django_control_components.studio as studio_pkg

    js = pathlib.Path(studio_pkg.__file__).parent / "static/dcc/dcc-studio.js"
    text = js.read_text()
    assert 'directive(\n      "recurse"' in text or 'directive("recurse"' in text
    assert 'data("dccTree"' in text
    assert "MAX_DEPTH = 12" in text  # mirrors deserialize._MAX_TREE_DEPTH


def test_nested_tree_from_the_editor_round_trips(client, urlconf, studio_user):
    page = Page.objects.create(title="Home", route="", tree={})
    client.force_login(studio_user)
    tree = {
        "id": "b1",
        "type": "AppShell",
        "props": {},
        "slots": {
            "sidebar": [{"id": "b2", "type": "Sidebar", "props": {"brand": "Admin"}, "slots": {}}],
            "content": [
                {
                    "id": "b3",
                    "type": "Grid",
                    "props": {"cols": 6},
                    "slots": {
                        "default": [
                            {"id": "b4", "type": "Column", "props": {"span": 3}, "slots": {}},
                        ]
                    },
                }
            ],
        },
    }
    response = client.post(
        f"/studio/pages/{page.pk}/save/", {"doc": json.dumps({"root": tree}), "revision": 0}
    )
    assert response.status_code == 200
    page.refresh_from_db()

    root = page.build_tree()
    assert root.slot_children("sidebar")[0].__class__.__name__ == "Sidebar"
    grid = root.slot_children("content")[0]
    assert grid.slot_children("default")[0].__class__.__name__ == "Column"


def test_editor_page_renders_the_recurse_template(client, urlconf, studio_user):
    page = Page.objects.create(title="Home", route="", tree={})
    client.force_login(studio_user)
    body = client.get(f"/studio/pages/{page.pk}/").content
    assert b'id="dcc-block-tpl"' in body
    assert b"x-recurse" in body
    assert b"dccTree(" in body
