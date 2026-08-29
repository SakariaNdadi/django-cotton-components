"""Model / field discovery and the spec path allowlist."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from django_control_components.studio.deserialize import validate_spec
from django_control_components.studio.introspect import (
    describe_model,
    installed_models,
    safe_paths,
)
from tests.testapp.models import Article

pytestmark = pytest.mark.django_db


def _request(user):
    from django.test import RequestFactory

    request = RequestFactory().get("/")
    request.user = user
    return request


def test_installed_models_hides_sensitive_and_unpermitted(rf, django_user_model):
    staff = django_user_model.objects.create_user("staff")
    labels = {row["label"] for row in installed_models(_request(staff))}
    assert "auth.group" not in labels
    assert "auth.permission" not in labels
    assert "contenttypes.contenttype" not in labels
    # no view_article permission yet
    assert "testapp.article" not in labels

    from django.contrib.auth.models import Permission

    staff.user_permissions.add(Permission.objects.get(codename="view_article"))
    staff = django_user_model.objects.get(pk=staff.pk)
    labels = {row["label"] for row in installed_models(_request(staff))}
    assert "testapp.article" in labels


def test_superuser_sees_user_model_but_staff_does_not(rf, django_user_model):
    root = django_user_model.objects.create_superuser("root", "r@x.io", "x")
    staff = django_user_model.objects.create_user("staff2")
    root_labels = {r["label"] for r in installed_models(_request(root))}
    staff_labels = {r["label"] for r in installed_models(_request(staff))}
    assert any(label.endswith(".user") for label in root_labels)
    assert not any(label.endswith(".user") for label in staff_labels)


def test_describe_model_suggests_types_and_skips_sensitive_fields():
    rows = {row["name"]: row for row in describe_model(Article)}
    assert rows["status"]["column_type"] == "BadgeColumn"  # has choices
    assert rows["featured"]["field_type"] == "Toggle"
    assert rows["published_at"]["entry_type"] == "DateEntry"
    assert rows["author"]["is_relation"] is True
    assert "tags" not in rows  # m2m is not a scalar cell


def test_safe_paths_allows_depth_one_fk_but_not_deeper():
    paths = safe_paths(Article)
    assert "title" in paths
    assert "author__name" in paths
    assert "author__articles__title" not in paths


def test_validate_spec_rejects_orm_traversal_oracle():
    spec = {
        "table": {
            "filters": [
                {"type": "Filter", "name": "x", "config": {"field": "author__name__password"}}
            ]
        }
    }
    with pytest.raises(ValidationError):
        validate_spec(spec, model=Article)


def test_validate_spec_rejects_all_fields_shortcut():
    with pytest.raises(ValidationError):
        validate_spec({"schema": {"fields": "__all__"}}, model=Article)


def test_validate_spec_accepts_a_clean_spec():
    spec = {
        "table": {
            "columns": [{"type": "TextColumn", "name": "title", "config": {"sortable": True}}]
        },
        "infolist": {"entries": [{"type": "TextEntry", "name": "author.name"}]},
    }
    validate_spec(spec, model=Article)  # no raise


def test_group_model_is_never_pickable(rf, django_user_model):
    root = django_user_model.objects.create_superuser("root2", "r2@x.io", "x")
    assert Group  # imported for clarity
    labels = {row["label"] for row in installed_models(_request(root))}
    assert "auth.group" not in labels
