from __future__ import annotations

import pytest
from django.test import Client
from django.urls import path

from django_cotton_components.schemas import Schema, TextInput
from django_cotton_components.wizards import WizardStep, WizardView
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
    import django_cotton_components.wizards.wizard as mod

    monkeypatch.setattr(mod, "_HAS_FORMTOOLS", False)
    with pytest.raises(RuntimeError, match="django-formtools"):
        DemoWizard.as_view()
