from __future__ import annotations

import threading

import pytest

from django_cotton_components.core import UNSET, AttributeBag, RenderContext
from django_cotton_components.core.component import Component, setter
from django_cotton_components.core.evaluate import ClosureInjectionError, evaluate


class Widget(Component):
    template_name = "x.html"

    @setter
    def label(self, value):
        return self._set("label", value)

    @setter
    def size(self, value):
        return self._set("size", value)


def test_make_and_chain_return_self():
    w = Widget.make("a").label("A").size(3)
    assert isinstance(w, Widget)
    assert w._get("label") == "A"
    assert w._get("size") == 3


def test_kwargs_equal_chained():
    a = Widget.make("f").label("L").size(2)
    b = Widget("f", label="L", size=2)
    assert a._config == b._config


def test_unknown_kwarg_lists_valid_setters():
    with pytest.raises(TypeError, match="no setter 'bogus'"):
        Widget("f", bogus=1)


def test_unset_is_falsy_and_distinct_from_none():
    assert not UNSET
    assert UNSET is not None
    w = Widget.make("f")
    assert w._get("label") is UNSET
    w.label(None)
    assert w._get("label") is None


def test_clone_isolates_config():
    a = Widget.make("f").label("A")
    b = a.clone().label("B")
    assert a._get("label") == "A"
    assert b._get("label") == "B"


def test_evaluate_injects_by_param_name():
    ctx = RenderContext(record={"k": 1})
    assert evaluate(lambda record: record["k"], ctx) == 1
    assert evaluate(42, ctx) == 42


def test_evaluate_rejects_unknown_param():
    with pytest.raises(ClosureInjectionError, match="wat"):
        evaluate(lambda wat: wat, RenderContext())


def test_visibility_closure():
    w = Widget.make("f").when(lambda record: record is not None)
    assert w.is_visible(RenderContext(record=object())) is True
    assert w.is_visible(RenderContext(record=None)) is False


def test_attribute_bag_merges_class_only():
    bag = AttributeBag({"class": "a b"}, {"class": "b c", "id": "x"})
    assert bag.as_dict() == {"class": "a b c", "id": "x"}


def test_attribute_bag_boolean_attr_render():
    assert 'required="required"' in AttributeBag({"required": True}).render()
    assert "required" not in AttributeBag({"required": False}).render()


def test_attribute_bag_rejects_unsafe_key():
    with pytest.raises(ValueError, match="Unsafe attribute name"):
        AttributeBag({'x="y" onload': "1"})


def test_component_instance_renders_concurrently_without_crosstalk(monkeypatch):
    seen: list[str] = []

    def fake_render(component, ctx):
        seen.append(ctx.record)
        return ""

    monkeypatch.setattr("django_cotton_components.core.renderer.render_component", fake_render)
    w = Widget.make("f")

    def run(tag):
        w.render(RenderContext(record=tag))

    threads = [threading.Thread(target=run, args=(f"r{i}",)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(seen) == sorted(f"r{i}" for i in range(20))
    assert w._config == {}  # render did not mutate config
