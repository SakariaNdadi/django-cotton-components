from __future__ import annotations

import pytest
from django.test import Client
from django.urls import path

from django_control_components.infolists import Infolist, TextEntry
from django_control_components.schemas import Schema, TextInput
from django_control_components.wizards import WizardStep, WizardView
from tests.testapp.forms import ArticleForm

pytestmark = pytest.mark.django_db


class DemoWizard(WizardView):
    steps_config = [
        WizardStep(
            "basics",
            Schema.make().form(ArticleForm).strict().schema([TextInput.make("title")]),
            title="Basics",
        ),
        WizardStep(
            "details",
            Schema.make().form(ArticleForm).strict().schema([TextInput.make("slug")]),
            title="Details",
        ),
    ]
    done_payload: dict = {}

    def done(self, form_list, **kwargs):
        from django.http import HttpResponse

        merged = {}
        for form in form_list:
            merged.update(form.cleaned_data)
        DemoWizard.done_payload = merged
        return HttpResponse("done")


urlpatterns = [path("wiz/", DemoWizard.as_view(), name="wiz")]


@pytest.fixture
def wiz_client(settings):
    settings.ROOT_URLCONF = "tests.test_wizard"
    return Client()


def test_form_list_derived_from_steps():
    assert list(dict(DemoWizard.form_list)) == ["basics", "details"]


def test_wizard_walks_steps_and_calls_done(wiz_client):
    c = wiz_client
    r = c.get("/wiz/")
    assert r.status_code == 200
    assert b"dcc-wizard" in r.content
    assert b'name="basics-title"' in r.content

    r = c.post("/wiz/", {"demo_wizard-current_step": "basics", "basics-title": "My Title"})
    assert r.status_code == 200
    assert b'name="details-slug"' in r.content  # advanced to step 2

    r = c.post("/wiz/", {"demo_wizard-current_step": "details", "details-slug": "my-title"})
    assert r.status_code == 200
    assert r.content == b"done"
    assert DemoWizard.done_payload["title"] == "My Title"
    assert DemoWizard.done_payload["slug"] == "my-title"


def test_wizard_step_validation_blocks_advance(wiz_client):
    c = wiz_client
    c.get("/wiz/")
    r = c.post("/wiz/", {"demo_wizard-current_step": "basics", "basics-title": ""})
    assert r.status_code == 200
    assert b'name="basics-title"' in r.content  # still on step 1
    assert b"dcc-field--invalid" in r.content


def test_as_view_requires_formtools(monkeypatch):
    import django_control_components.wizards.wizard as mod

    monkeypatch.setattr(mod, "_HAS_FORMTOOLS", False)
    with pytest.raises(RuntimeError, match="django-formtools"):
        DemoWizard.as_view()


# -- polymorphic step bodies --------------------------------------------------


class RichWizard(WizardView):
    steps_config = [
        WizardStep("intro", "<p data-intro>Welcome to the flow</p>", title="Start"),
        WizardStep(
            "basics",
            Schema.make().form(ArticleForm).strict().schema([TextInput.make("title")]),
            title="Basics",
        ),
        WizardStep(
            "note",
            lambda view: f"<p data-note>step is {view.steps.current}</p>",
            title="Note",
        ),
        WizardStep(
            "review",
            Infolist.make().schema([TextEntry.make("title")]),
            title="Review",
            heading="Confirm",
            description="Nothing saved yet.",
            record=lambda view: view.get_all_cleaned_data(),
        ),
    ]
    wizard_class = "themed"
    wizard_attrs = {"style": "--dcc-wizard-bg:#0b1120"}
    done_payload: dict = {}

    def done(self, form_list, **kwargs):
        from django.http import HttpResponse

        merged = {}
        for form in form_list:
            merged.update(form.cleaned_data)
        RichWizard.done_payload = merged
        return HttpResponse("done")


urlpatterns += [path("rw/", RichWizard.as_view(), name="rw")]


@pytest.fixture
def rich_client(settings):
    settings.ROOT_URLCONF = "tests.test_wizard"
    return Client()


def test_string_body_step_renders_and_advances(rich_client):
    r = rich_client.get("/rw/")
    assert b"<p data-intro>Welcome to the flow</p>" in r.content
    assert b'name="intro-' not in r.content  # no form fields

    r = rich_client.post("/rw/", {"rich_wizard-current_step": "intro"})
    assert b'name="basics-title"' in r.content  # advanced past the content step


def test_callable_body_gets_view(rich_client):
    rich_client.get("/rw/")
    rich_client.post("/rw/", {"rich_wizard-current_step": "intro"})
    r = rich_client.post(
        "/rw/", {"rich_wizard-current_step": "basics", "basics-title": "Hi"}
    )
    assert b"<p data-note>step is note</p>" in r.content


def test_infolist_review_step_shows_prior_data(rich_client):
    rich_client.get("/rw/")
    rich_client.post("/rw/", {"rich_wizard-current_step": "intro"})
    rich_client.post(
        "/rw/", {"rich_wizard-current_step": "basics", "basics-title": "My Title"}
    )
    r = rich_client.post("/rw/", {"rich_wizard-current_step": "note"})
    assert b"My Title" in r.content  # infolist rendered get_all_cleaned_data()
    assert b"Confirm" in r.content and b"Nothing saved yet." in r.content


def test_goto_button_only_for_prior_steps(rich_client):
    rich_client.get("/rw/")
    r = rich_client.post("/rw/", {"rich_wizard-current_step": "intro"})
    assert b'name="wizard_goto_step" value="intro"' in r.content  # can go back
    assert b'value="note"' not in r.content  # cannot jump forward


def test_theming_hooks_on_wrapper(rich_client):
    r = rich_client.get("/rw/")
    assert b'class="dcc-wizard themed"' in r.content
    assert b"--dcc-wizard-bg:#0b1120" in r.content


def test_empty_form_body_never_blocks_done(rich_client):
    rich_client.get("/rw/")
    rich_client.post("/rw/", {"rich_wizard-current_step": "intro"})
    rich_client.post(
        "/rw/", {"rich_wizard-current_step": "basics", "basics-title": "T"}
    )
    rich_client.post("/rw/", {"rich_wizard-current_step": "note"})
    r = rich_client.post("/rw/", {"rich_wizard-current_step": "review"})
    assert r.content == b"done"
    assert RichWizard.done_payload["title"] == "T"


def test_htmx_done_redirect_promoted_to_hx_redirect(wiz_client):
    c = wiz_client
    c.get("/wiz/")
    c.post("/wiz/", {"demo_wizard-current_step": "basics", "basics-title": "T"})
    r = c.post(
        "/wiz/",
        {"demo_wizard-current_step": "details", "details-slug": "t"},
        HTTP_HX_REQUEST="true",
    )
    # DemoWizard.done() returns HttpResponse("done"), not a redirect -> untouched
    assert r.content == b"done"


def test_htmx_done_redirect_uses_hx_redirect_header(rich_client):
    from django.http import HttpResponseRedirect

    original_done = RichWizard.__dict__["done"]
    RichWizard.done = lambda self, form_list, **kw: HttpResponseRedirect("/after/")
    try:
        c = rich_client
        c.get("/rw/")
        c.post("/rw/", {"rich_wizard-current_step": "intro"})
        c.post("/rw/", {"rich_wizard-current_step": "basics", "basics-title": "T"})
        c.post("/rw/", {"rich_wizard-current_step": "note"})
        r = c.post(
            "/rw/", {"rich_wizard-current_step": "review"}, HTTP_HX_REQUEST="true"
        )
        assert r.status_code == 204
        assert r["HX-Redirect"] == "/after/"
    finally:
        RichWizard.done = original_done


def test_step_schema_backcompat_property():
    intro, basics = RichWizard.steps_config[0], RichWizard.steps_config[1]
    assert intro.schema is None and intro.is_form is False
    assert basics.schema is not None and basics.is_form is True
