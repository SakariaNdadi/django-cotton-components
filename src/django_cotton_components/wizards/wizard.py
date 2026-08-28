"""Multi-step forms on top of django-formtools.

``django-formtools`` already solves step storage, file handling between steps,
step re-entry and ``done()``. DCC's :class:`WizardView` subclasses its
``SessionWizardView`` and swaps only the rendering layer.

A step's ``body`` is polymorphic:

* a DCC :class:`~django_cotton_components.schemas.schema.Schema` — a form step,
  validated by Django's ``form.is_valid()`` (there is no parallel system);
* a DCC :class:`~django_cotton_components.infolists.infolist.Infolist` — a
  read-only detail step (an intro screen, a review of collected data);
* a string / ``SafeString`` — raw markup;
* a callable ``view -> str`` — markup that needs live data.

Non-form bodies get an empty always-valid form, so they never block ``Next``.

Requires ``pip install django-cotton-components[wizard]``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, ClassVar

from django import forms
from django.forms.utils import flatatt
from django.utils.safestring import SafeString

try:
    from formtools.wizard.views import SessionWizardView  # type: ignore[import-untyped]

    _HAS_FORMTOOLS = True
except ImportError:  # pragma: no cover - exercised only without the extra
    SessionWizardView = object
    _HAS_FORMTOOLS = False

if TYPE_CHECKING:
    from django.forms import BaseForm
    from django.http import HttpRequest, HttpResponse

    from ..schemas.schema import Schema


class _EmptyForm(forms.Form):
    """Placeholder form for a non-form step — always valid, no fields."""


def _default_file_storage() -> Any:
    from pathlib import Path

    from django.conf import settings
    from django.core.files.storage import FileSystemStorage

    root = Path(getattr(settings, "MEDIA_ROOT", "") or ".") / "dcc-wizard-tmp"
    return FileSystemStorage(location=str(root))


@dataclass
class WizardStep:
    name: str
    body: Any  # Schema | Infolist | str | SafeString | Callable[[view], str]
    title: str = ""
    heading: str = ""
    description: str = ""
    record: Callable[[Any], Any] | None = None

    @property
    def is_form(self) -> bool:
        from ..schemas.schema import Schema

        return isinstance(self.body, Schema)

    @property
    def schema(self) -> Schema | None:
        """The step's :class:`Schema` when it is a form step, else ``None``."""
        return self.body if self.is_form else None

    @property
    def form_class(self) -> type[BaseForm]:
        # a form step is self-contained — only the fields it declares
        return self.body.to_form_class() if self.is_form else _EmptyForm

    def render_body(self, view: Any, form: BaseForm) -> SafeString:
        from ..infolists.infolist import Infolist
        from ..schemas.schema import Schema

        body = self.body
        if isinstance(body, Schema):
            return body.render(request=view.request, form=form)
        if isinstance(body, Infolist):
            record = self.record(view) if self.record else None
            if isinstance(record, dict):
                record = SimpleNamespace(**record)
            return body.render(request=view.request, record=record)
        if callable(body):
            return SafeString(str(body(view)))
        return SafeString(str(body))


class WizardView(SessionWizardView):  # type: ignore[misc]
    """Subclass and set ``steps_config`` to a list of :class:`WizardStep`.

    ``form_list`` and per-step rendering are derived from it. Chrome is themed
    per subclass via ``wizard_class`` / ``wizard_attrs`` (a ``style`` string
    setting ``--dcc-wizard-*`` custom properties is the intended path) and the
    step indicator can be dropped with ``show_step_nav = False``.
    """

    steps_config: ClassVar[list[WizardStep]] = []
    template_name = "django_cotton_components/wizards/wizard.html"

    wizard_class: ClassVar[str] = ""
    wizard_attrs: ClassVar[dict[str, Any]] = {}
    show_step_nav: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.steps_config:
            cls.form_list = [(s.name, s.form_class) for s in cls.steps_config]
            if getattr(cls, "file_storage", None) is None and _HAS_FORMTOOLS:
                cls.file_storage = _default_file_storage()

    @classmethod
    def as_view(cls, **initkwargs: Any) -> Any:
        if not _HAS_FORMTOOLS:
            raise RuntimeError(
                "WizardView needs django-formtools. Install django-cotton-components[wizard]."
            )
        return super().as_view(**initkwargs)

    def _step(self, name: str) -> WizardStep:
        return next(s for s in self.steps_config if s.name == name)

    @property
    def wizard_id(self) -> str:
        return f"dcc-wizard-{type(self).__name__.lower()}"

    def _all_data(self) -> dict[str, Any]:
        try:
            return self.get_all_cleaned_data()
        except Exception:  # a prior step is invalid — nothing to show yet
            return {}

    def _steps_meta(self) -> list[dict[str, Any]]:
        names = [s.name for s in self.steps_config]
        current = names.index(self.steps.current)
        meta = []
        for index, step in enumerate(self.steps_config):
            meta.append(
                {
                    "name": step.name,
                    "title": step.title or step.name.title(),
                    "is_current": index == current,
                    "is_done": index < current,
                    "can_goto": index < current,
                }
            )
        return meta

    def get_context_data(self, form: BaseForm, **kwargs: Any) -> dict[str, Any]:
        from .. import htmx

        context = super().get_context_data(form=form, **kwargs)
        step = self._step(self.steps.current)
        step_html = step.render_body(self, form)

        context["step_html"] = step_html
        context["schema_html"] = step_html  # back-compat alias
        context["step_heading"] = step.heading
        context["step_description"] = step.description
        context["all_data"] = self._all_data()

        steps_meta = self._steps_meta()
        context["steps"] = steps_meta
        context["step_titles"] = [(m["name"], m["title"]) for m in steps_meta]  # back-compat
        context["current_step"] = self.steps.current

        context["wizard_id"] = self.wizard_id
        context["wizard_class"] = self.wizard_class
        context["wizard_attrs_html"] = SafeString(flatatt(self.wizard_attrs))
        context["show_step_nav"] = self.show_step_nav

        # Each step submits over htmx and swaps only the wizard node back in
        # (hx-select pulls it out of the full page the view still renders, so
        # the no-JS path is unchanged).
        context["wizard_htmx"] = htmx.post(
            self.request.path,
            request=self.request,
            target=f"#{self.wizard_id}",
            select=f"#{self.wizard_id}",
            swap="outerHTML",
        )
        return context

    def render_done(self, form: BaseForm, **kwargs: Any) -> HttpResponse:
        from .. import htmx

        # formtools already guarantees earlier steps validated before reaching
        # done(); re-assert it so a hand-crafted POST cannot skip ahead.
        for name in self.get_form_list():
            f = self.get_form(
                step=name,
                data=self.storage.get_step_data(name),
                files=self.storage.get_step_files(name),
            )
            if not f.is_valid():
                return self.render_revalidation_failure(name, f, **kwargs)
        response = super().render_done(form, **kwargs)
        # Each step swaps only the wizard node, so a plain 3xx from done() would
        # be followed by htmx and its body selected into the (now absent) wizard
        # node — blanking the page. Promote it to a real browser navigation.
        if (
            htmx.is_htmx(self.request)
            and getattr(response, "status_code", None) in (301, 302)
            and response.get("Location")
        ):
            return htmx.response.redirect(response["Location"])
        return response

    def done(
        self, form_list: Any, **kwargs: Any
    ) -> HttpResponse:  # pragma: no cover - user override
        raise NotImplementedError("Implement done() to persist the collected data.")


def wizard_request_ok(request: HttpRequest) -> bool:  # pragma: no cover - trivial
    return request.method in ("GET", "POST")
