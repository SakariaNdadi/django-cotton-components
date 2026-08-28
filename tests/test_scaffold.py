"""Auto-scaffolding a working spec from a model."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from django_cotton_components.studio.deserialize import (
    build_infolist_from_spec,
    build_schema_from_spec,
    build_table_from_spec,
)
from django_cotton_components.studio.models import DashboardSpec
from django_cotton_components.studio.scaffold import scaffold_spec
from tests.testapp.models import Article

pytestmark = pytest.mark.django_db


def test_scaffold_spec_round_trips_and_renders(rf, article):
    spec = scaffold_spec(Article)

    table = build_table_from_spec(Article.objects.all(), spec["table"])
    assert str(table.render(rf.get("/")))

    schema = build_schema_from_spec(Article, spec["schema"])
    assert schema.build_form(instance=article).fields  # a real bound form

    infolist = build_infolist_from_spec(Article, spec["infolist"])
    assert str(infolist.render(request=rf.get("/"), record=article))


def test_scaffolded_spec_saves_as_a_dashboardspec():
    spec = scaffold_spec(Article)
    obj = DashboardSpec.objects.create(
        slug="article", label="Articles", model="testapp.Article", **spec
    )
    assert obj.pk
    # the scaffolded schema carries an explicit field list, never "__all__"
    assert isinstance(obj.schema["fields"], list)


def test_scaffold_user_model_omits_password():
    spec = scaffold_spec(get_user_model())
    dumped = str(spec)
    assert "password" not in dumped
    assert "is_superuser" not in dumped


def test_scaffold_table_has_choice_filter_and_default_sort():
    table = scaffold_spec(Article)["table"]
    assert any(f["type"] == "SelectFilter" and f["name"] == "status" for f in table["filters"])
    assert table["default_sort"] in {"-created_at", "-published_at"}


def test_dcc_scaffold_command_dry_run(capsys):
    call_command("dcc_scaffold", "testapp.article", "--dry-run")
    out = capsys.readouterr().out
    assert "testapp.article" in out
    assert not DashboardSpec.objects.exists()


def test_dcc_scaffold_command_writes_rows():
    call_command("dcc_scaffold", "testapp.article")
    assert DashboardSpec.objects.filter(slug="article").exists()
