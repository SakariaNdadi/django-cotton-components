from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from django_cotton_components.actions import Action, BulkAction, registry
from django_cotton_components.actions.endpoints import ActionView
from django_cotton_components.tables import SelectFilter, Table, TextColumn
from tests.testapp.models import Article, Author

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_registry():
    registry.clear()
    yield
    registry.clear()


@pytest.fixture
def data():
    ada = Author.objects.create(name="Ada")
    arts = [
        Article.objects.create(title=f"A{i}", slug=f"a{i}", status="draft", author=ada)
        for i in range(4)
    ]
    return ada, arts


def _table(qs, actions=None, bulk=None) -> Table:
    t = Table.make(qs).columns([TextColumn.make("title")]).id("art")
    if actions:
        t = t.actions(actions)
    if bulk:
        t = t.bulk_actions(bulk)
    return t


def test_unknown_owner_and_action_are_404():
    assert registry.resolve("nope", "x") is None


def test_table_registers_actions_on_render(data):
    calls: list = []

    action = Action.make("publish").action(lambda record: calls.append(record.pk))
    _table(Article.objects.all(), actions=[action]).render(RequestFactory().get("/"))
    assert registry.resolve("table-art", "publish") is not None


def test_action_trigger_hidden_when_unauthorized(data):
    _, arts = data
    action = Action.make("danger").authorize(lambda user: False)
    _table(Article.objects.all(), actions=[action]).render(RequestFactory().get("/"))
    req = RequestFactory().get("/")
    req.user = AnonymousUser()
    assert str(action.render_trigger(record=arts[0], request=req)) == ""


def test_execute_runs_callback_and_returns_trigger(data):
    _, arts = data
    seen = []
    action = Action.make("touch").action(lambda record: seen.append(record.pk))
    _table(Article.objects.all(), actions=[action]).render(RequestFactory().get("/"))

    req = RequestFactory().post("/dcc/a/table-art/touch/", {"record": arts[1].pk})
    req.user = AnonymousUser()
    resp = ActionView.as_view()(req, owner_key="table-art", action_name="touch")
    assert resp.status_code == 204
    assert "HX-Trigger" in resp
    assert seen == [arts[1].pk]


def test_execute_denied_when_hidden_action_posted(data):
    _, arts = data
    action = Action.make("secret").authorize(lambda user: False).action(lambda record: 1 / 0)
    _table(Article.objects.all(), actions=[action]).render(RequestFactory().get("/"))
    req = RequestFactory().post("/x/", {"record": arts[0].pk})
    req.user = AnonymousUser()
    resp = ActionView.as_view()(req, owner_key="table-art", action_name="secret")
    assert resp.status_code == 403


def test_bulk_action_rescopes_to_filtered_queryset(data):
    _, arts = data
    # table only exposes 'live' articles; all fixtures start 'draft'
    Article.objects.filter(pk=arts[0].pk).update(status="live")
    seen = {}
    bulk = BulkAction.make("archive").action(lambda records: seen.update({"n": len(records)}))
    table = (
        Table.make(Article.objects.all())
        .columns([TextColumn.make("title")])
        .id("art")
        .filters([SelectFilter.make("status").options(Article.Status.choices)])
        .bulk_actions([bulk])
    )
    table.render(RequestFactory().get("/", {"t_art_f_status": "live"}))

    # attacker submits ALL pks, but table is scoped to status=live
    req = RequestFactory().post("/x/?t_art_f_status=live", {"records": [a.pk for a in arts]})
    req.user = AnonymousUser()
    resp = ActionView.as_view()(req, owner_key="table-art", action_name="archive")
    assert resp.status_code == 204
    assert seen["n"] == 1  # only the one live article, not all four


def test_bulk_select_all_matching_uses_the_filtered_queryset(data):
    _, arts = data
    Article.objects.filter(pk=arts[0].pk).update(status="live")
    Article.objects.filter(pk=arts[1].pk).update(status="live")
    seen = {}

    def run(records):
        # records is the queryset itself (unmaterialised) when select_all
        seen["type"] = type(records).__name__
        seen["n"] = records.count() if hasattr(records, "count") else len(records)

    bulk = BulkAction.make("archive").action(run)
    table = (
        Table.make(Article.objects.all())
        .columns([TextColumn.make("title")])
        .id("art")
        .filters([SelectFilter.make("status").options(Article.Status.choices)])
        .bulk_actions([bulk])
    )
    table.render(RequestFactory().get("/", {"t_art_f_status": "live"}))

    req = RequestFactory().post("/x/?t_art_f_status=live&select_all=1", {"select_all": "1"})
    req.user = AnonymousUser()
    resp = ActionView.as_view()(req, owner_key="table-art", action_name="archive")
    assert resp.status_code == 204
    assert seen["n"] == 2  # both live rows, never a pk list


def test_action_with_schema_renders_modal_on_get(data):
    from django_cotton_components.schemas import Schema, TextInput
    from tests.testapp.forms import ArticleForm

    _, arts = data
    schema = Schema.make().form(ArticleForm).strict().schema([TextInput.make("title")])
    action = Action.make("edit_title").schema(schema).action(lambda record, data: None)
    _table(Article.objects.all(), actions=[action]).render(RequestFactory().get("/"))

    req = RequestFactory().get("/dcc/a/table-art/edit_title/", {"record": arts[0].pk})
    req.user = AnonymousUser()
    resp = ActionView.as_view()(req, owner_key="table-art", action_name="edit_title")
    assert resp.status_code == 200
    assert b"dcc-modal__dialog" in resp.content
    assert b'name="title"' in resp.content


def test_modal_schema_action_saves_via_standalone_form(data):
    """A strict .modal(schema) action must bind only its declared fields, not
    the whole ModelForm (whose slug/author would fail validation)."""
    from django_cotton_components.schemas import Schema, TextInput
    from tests.testapp.forms import ArticleForm

    _, arts = data
    schema = Schema.make().form(ArticleForm).strict().schema([TextInput.make("title")])
    saved = {}
    action = (
        Action.make("edit_title")
        .modal(schema)
        .action(lambda record, data: saved.update(pk=record.pk, title=data["title"]))
    )
    _table(Article.objects.all(), actions=[action]).render(RequestFactory().get("/"))

    req = RequestFactory().post(
        f"/dcc/a/table-art/edit_title/?record={arts[0].pk}", {"title": "renamed"}
    )
    req.user = AnonymousUser()
    resp = ActionView.as_view()(req, owner_key="table-art", action_name="edit_title")

    assert saved == {"pk": arts[0].pk, "title": "renamed"}
    # empty 200 clears the modal mount; HX-Trigger still refreshes the table
    assert resp.status_code == 200
    assert resp.content == b""
    assert "dcc:refresh" in resp["HX-Trigger"]


def test_inline_action_keeps_204(data):
    _, arts = data
    hit = {}
    action = Action.make("bump").action(lambda record: hit.setdefault("pk", record.pk))
    _table(Article.objects.all(), actions=[action]).render(RequestFactory().get("/"))

    req = RequestFactory().post(f"/dcc/a/table-art/bump/?record={arts[0].pk}")
    req.user = AnonymousUser()
    resp = ActionView.as_view()(req, owner_key="table-art", action_name="bump")

    assert hit == {"pk": arts[0].pk}
    assert resp.status_code == 204


def test_collapsed_actions_render_in_a_menu(data):
    _, _arts = data
    table = _table(
        Article.objects.all(),
        actions=[
            Action.make("edit").label("Edit"),
            Action.make("archive").label("Archive").collapsed(),
        ],
    )
    html = str(table.render(RequestFactory().get("/")))
    assert html.count('class="dcc-menu"') == Article.objects.count()
    assert "Edit" in html and "Archive" in html
