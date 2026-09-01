"""The ``Page`` model: block-tree hydration, the spec-migration read path, the
reused deserialize sandbox, and server-side ``perms`` pruning."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser, Permission
from django.core.exceptions import ValidationError

from django_control_components.blocks import Column, Grid
from django_control_components.studio.deserialize import _MAX_SPEC_BYTES, build_block_tree_from_spec
from django_control_components.studio.models import Page, SpecRevision, Visibility

pytestmark = pytest.mark.django_db


def _grid_tree() -> dict:
    return {
        "id": "root",
        "type": "Grid",
        "props": {"cols": 6},
        "slots": {
            "default": [
                {"id": "c1", "type": "Column", "props": {"span": 3}, "slots": {"default": []}},
            ]
        },
    }


class _FakeUser:
    def __init__(self, *, authenticated=True, superuser=False, perms=()):
        self.is_authenticated = authenticated
        self.is_superuser = superuser
        self._perms = set(perms)

    def has_perm(self, perm, obj=None):
        return perm in self._perms


class _Req:
    def __init__(self, user):
        self.user = user


# -- model + read path ------------------------------------------------


def test_envelope_wraps_tree_with_schema_version():
    page = Page(title="Home", tree=_grid_tree(), schema_version=0)
    env = page.envelope()
    assert env["schema_version"] == 0
    assert env["root"]["type"] == "Grid"


def test_document_runs_migrate_and_caches():
    page = Page(title="Home", tree=_grid_tree())
    first = page.document
    assert first is page.document  # memoised on the instance
    assert first["root"]["type"] == "Grid"


def test_build_tree_hydrates_registered_blocks():
    page = Page(title="Home", tree=_grid_tree())
    root = page.build_tree()
    assert isinstance(root, Grid)
    children = root.slot_children("default")
    assert len(children) == 1 and isinstance(children[0], Column)


def test_build_tree_returns_none_for_empty_page():
    assert Page(title="Blank", tree={}).build_tree() is None


def test_clean_reports_a_bad_tree_under_the_tree_key():
    page = Page(title="Bad", tree={"type": "NoSuchBlock", "slots": {}})
    with pytest.raises(ValidationError) as exc:
        page.clean()
    assert "tree" in exc.value.message_dict


# -- reused deserialize sandbox -------------------------------------


def test_hydration_rejects_an_oversized_document():
    big = {"type": "Grid", "props": {"pad": "x" * _MAX_SPEC_BYTES}, "slots": {"default": []}}
    with pytest.raises(ValidationError, match="ceiling"):
        build_block_tree_from_spec({"schema_version": 0, "root": big})


def test_hydration_rejects_nesting_past_the_depth_ceiling():
    node = {"type": "Column", "props": {}, "slots": {"default": []}}
    for _ in range(14):
        node = {"type": "Column", "props": {}, "slots": {"default": [node]}}
    with pytest.raises(ValidationError, match="nesting exceeds"):
        build_block_tree_from_spec({"schema_version": 0, "root": node})


def test_hydration_rejects_a_code_only_setter_in_props():
    tree = {"type": "Grid", "props": {"visible": "lambda r: True"}, "slots": {"default": []}}
    with pytest.raises(ValidationError, match="code, not configuration"):
        build_block_tree_from_spec({"schema_version": 0, "root": tree})


def test_hydration_rejects_a_non_object_node():
    tree = {"type": "Grid", "props": {}, "slots": {"default": ["nope"]}}
    with pytest.raises(ValidationError, match="expected a block node"):
        build_block_tree_from_spec({"schema_version": 0, "root": tree})


# -- server-side perms gate ---------------------------------------


def _gated_tree() -> dict:
    return {
        "type": "Grid",
        "props": {},
        "slots": {
            "default": [
                {
                    "type": "Column",
                    "props": {},
                    "perms": ["tests.view_article"],
                    "slots": {"default": []},
                }
            ]
        },
    }


def test_perms_gate_prunes_a_node_for_a_user_without_the_permission():
    root = build_block_tree_from_spec(
        {"schema_version": 0, "root": _gated_tree()},
        request=_Req(_FakeUser(perms=())),
    )
    assert root.slot_children("default") == []


def test_perms_gate_keeps_a_node_for_a_permitted_user():
    root = build_block_tree_from_spec(
        {"schema_version": 0, "root": _gated_tree()},
        request=_Req(_FakeUser(perms=["tests.view_article"])),
    )
    assert len(root.slot_children("default")) == 1


def test_perms_gate_prunes_for_anonymous():
    root = build_block_tree_from_spec(
        {"schema_version": 0, "root": _gated_tree()},
        request=_Req(AnonymousUser()),
    )
    assert root.slot_children("default") == []


# -- visibility + persistence -------------------------------------


def test_page_visibility_is_the_three_state_field(django_user_model):
    public = Page.objects.create(title="About", route="about", visibility=Visibility.PUBLIC)
    assert public.is_visible_to(AnonymousUser()) is True

    restricted = Page.objects.create(title="Ops", route="ops", visibility=Visibility.RESTRICTED)
    assert restricted.is_visible_to(AnonymousUser()) is False


def test_mount_panel_route_is_unique_together():
    Page.objects.create(title="One", mount="site", panel="", route="about")
    with pytest.raises(ValidationError):
        Page.objects.create(title="Two", mount="site", panel="", route="about")


def test_spec_revision_links_to_a_page(django_user_model):
    page = Page.objects.create(title="Home", route="")
    rev = SpecRevision.objects.create(page=page, payload={"root": {}})
    assert list(page.revisions.all()) == [rev]


def test_permission_gate_is_anded(django_user_model):
    user = _FakeUser(perms=["a.one"])
    tree = {
        "type": "Grid",
        "props": {},
        "slots": {
            "default": [
                {
                    "type": "Column",
                    "props": {},
                    "perms": ["a.one", "a.two"],
                    "slots": {"default": []},
                }
            ]
        },
    }
    root = build_block_tree_from_spec({"schema_version": 0, "root": tree}, request=_Req(user))
    assert root.slot_children("default") == []


def test_superuser_bypasses_the_perms_gate():
    root = build_block_tree_from_spec(
        {"schema_version": 0, "root": _gated_tree()},
        request=_Req(_FakeUser(superuser=True, perms=())),
    )
    assert len(root.slot_children("default")) == 1


def test_real_permission_string_resolves(client, django_user_model):
    user = django_user_model.objects.create_user("ed", password="x")
    perm = Permission.objects.get(codename="use_studio")
    user.user_permissions.add(perm)
    user = django_user_model.objects.get(pk=user.pk)
    tree = {
        "type": "Grid",
        "props": {},
        "slots": {
            "default": [
                {
                    "type": "Column",
                    "props": {},
                    "perms": ["dcc_studio.use_studio"],
                    "slots": {"default": []},
                }
            ]
        },
    }
    root = build_block_tree_from_spec({"schema_version": 0, "root": tree}, request=_Req(user))
    assert len(root.slot_children("default")) == 1
