from __future__ import annotations

import pytest
from django.test import RequestFactory

from django_control_components.core.component import UNSET, Component, setter
from django_control_components.core.context import RenderContext
from django_control_components.core.evaluate import evaluate


class W(Component):
    template_name = "x.html"

    @setter
    def label(self, v):
        return self._set("label", v)


def test_context_user_and_resolve():
    req = RequestFactory().get("/")
    req.user = "ada"
    ctx = RenderContext(request=req, record={"a": 1}, operation="edit")
    assert ctx.user == "ada"
    assert ctx.resolve("user") == "ada"
    assert ctx.resolve("operation") == "edit"
    assert ctx.resolve("context") is ctx
    assert ctx.resolve("record") == {"a": 1}


def test_context_child_overrides():
    ctx = RenderContext(operation="create")
    child = ctx.child(operation="edit")
    assert child.operation == "edit"
    assert ctx.operation == "create"


def test_state_reader_get():
    from tests.testapp.forms import ArticleForm

    form = ArticleForm(initial={"title": "Hi"})
    ctx = RenderContext(form=form)
    getter = ctx.resolve("get")
    assert getter("title") == "Hi"
    assert getter("nonexistent", "fallback") == "fallback"


def test_state_reader_no_form():
    getter = RenderContext().resolve("get")
    assert getter("anything", "d") == "d"


def test_noop_setter_is_callable():
    RenderContext().resolve("set")("x", 1)


def test_evaluate_with_get_injection():
    from tests.testapp.forms import ArticleForm

    ctx = RenderContext(form=ArticleForm(initial={"status": "live"}))
    assert evaluate(lambda get: get("status"), ctx) == "live"


def test_evaluate_class_passthrough():
    assert evaluate(int, RenderContext()) is int


def test_component_extra_attributes_merge():
    w = W.make("f").extra_attributes({"data-a": "1"}).extra_attributes({"data-b": "2"})
    assert w._get("extra_attributes") == {"data-a": "1", "data-b": "2"}


def test_component_hidden_when():
    w = W.make("f").hidden_when(lambda record: record == "hide")
    assert w.is_visible(RenderContext(record="hide")) is False
    assert w.is_visible(RenderContext(record="show")) is True


def test_component_when_static_false():
    assert W.make("f").when(False).is_visible(RenderContext()) is False


def test_render_returns_empty_when_hidden(monkeypatch):
    w = W.make("f").visible(False)
    assert str(w.render(RenderContext())) == ""


def test_clone_children_isolated():
    parent = W.make("p")
    parent._children = [W.make("c").label("orig")]
    clone = parent.clone()
    clone._children[0].label("new")
    assert parent._children[0]._get("label") == "orig"


def test_unset_repr():
    assert repr(UNSET) == "UNSET"


def test_renderer_requires_template_name():
    class NoTpl(Component):
        pass

    with pytest.raises(ValueError, match="no template_name"):
        NoTpl().render(RenderContext())
