"""Multi-step forms on top of django-formtools.

``django-formtools`` already solves step storage, file handling between steps,
step re-entry and ``done()``. DCC's :class:`WizardView` subclasses its
``SessionWizardView`` and swaps only the rendering layer for a DCC
:class:`~django_cotton_components.schemas.schema.Schema` per step. Per-step
validation is Django's ``form.is_valid()`` — there is no parallel validation
system.

Requires ``pip install django-cotton-components[wizard]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

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


def _default_file_storage() -> Any:
    from pathlib import Path

    from django.conf import settings
    from django.core.files.storage import FileSystemStorage

    root = Path(getattr(settings, "MEDIA_ROOT", "") or ".") / "dcc-wizard-tmp"
    return FileSystemStorage(location=str(root))


@dataclass
class WizardStep:
    name: str
    schema: Schema
    title: str = ""

    @property
    def form_class(self) -> type[BaseForm]:
        # a step is self-contained — only the fields it declares
        return self.schema.to_form_class()


class WizardView(SessionWizardView):  # type: ignore[misc]
    """Subclass and set ``steps_config`` to a list of :class:`WizardStep`.

    ``form_list`` and per-step schema rendering are derived from it.
    """

    steps_config: ClassVar[list[WizardStep]] = []
    template_name = "django_cotton_components/wizards/wizard.html"

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

    def get_context_data(self, form: BaseForm, **kwargs: Any) -> dict[str, Any]:
        from .. import htmx

        context = super().get_context_data(form=form, **kwargs)
        step = self._step(self.steps.current)
        context["schema_html"] = step.schema.render(request=self.request, form=form)
        context["step_titles"] = [(s.name, s.title or s.name.title()) for s in self.steps_config]
        context["current_step"] = self.steps.current
        context["wizard_id"] = self.wizard_id
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
        return super().render_done(form, **kwargs)

    def done(
        self, form_list: Any, **kwargs: Any
    ) -> HttpResponse:  # pragma: no cover - user override
        raise NotImplementedError("Implement done() to persist the collected data.")


def wizard_request_ok(request: HttpRequest) -> bool:  # pragma: no cover - trivial
    return request.method in ("GET", "POST")
