from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from django.forms import BaseForm, ModelForm, modelform_factory
from django.template.loader import render_to_string
from django.utils.safestring import SafeString, mark_safe

from ..core.component import Component
from ..core.context import RenderContext
from . import forms_bridge

if TYPE_CHECKING:
    from collections.abc import Iterator

    from django.db.models import Model
    from django.http import HttpRequest


class Schema:
    """Declarative description of a form's layout and presentation.

    Decorates an existing ``Form``/``ModelForm`` (``.form(...)``) or a model
    (``.model(...)`` -> ``modelform_factory``). Validation always runs through
    the Django form; this class never validates.
    """

    template_name = "django_cotton_components/schema.html"

    def __init__(self) -> None:
        self._form_class: type[BaseForm] | None = None
        self._model: type[Model] | None = None
        self._model_fields: list[str] | str = "__all__"
        self._components: list[Component] = []
        self._append_unmapped = True

    @classmethod
    def make(cls) -> Self:
        return cls()

    # -- configuration --------------------------------------------------

    def form(self, form_class: type[BaseForm]) -> Self:
        self._form_class = form_class
        return self

    def model(self, model: type[Model], *, fields: list[str] | str = "__all__") -> Self:
        self._model = model
        self._model_fields = fields
        return self

    def schema(self, components: list[Component]) -> Self:
        self._components = list(components)
        return self

    components = schema

    def strict(self, value: bool = True) -> Self:
        self._append_unmapped = not value
        return self

    # -- access -------------------------------------------------------

    @property
    def component_list(self) -> list[Component]:
        return self._components

    def get_form_class(self) -> type[BaseForm]:
        if self._form_class is not None:
            return self._form_class
        if self._model is not None:
            return modelform_factory(self._model, fields=self._model_fields)
        raise ValueError("Schema needs .form(FormClass) or .model(Model) before rendering")

    def is_modelform(self) -> bool:
        return issubclass(self.get_form_class(), ModelForm)

    def to_form_class(self) -> type[BaseForm]:
        """A real Django form containing only this schema's declared fields.

        Used where a schema must stand alone (wizard steps, action modals,
        filter forms). Goes back through the same bind/render path — one
        validation path, always Django's.
        """
        names = [f.name for f in self.iter_fields() if f.name]
        base = self.get_form_class()
        if issubclass(base, ModelForm):
            model = base._meta.model
            return modelform_factory(model, form=base, fields=names)

        from django import forms

        base_fields = getattr(base, "base_fields", {})
        attrs = {name: base_fields[name] for name in names if name in base_fields}
        return type("SchemaForm", (forms.Form,), attrs)

    def build_form(self, *args: Any, **kwargs: Any) -> BaseForm:
        if not self.is_modelform():
            kwargs.pop("instance", None)
        form = self.get_form_class()(*args, **kwargs)
        forms_bridge.check_alignment(self, form)
        self._attach_image_validators(form)
        return form

    def build_standalone_form(self, *args: Any, **kwargs: Any) -> BaseForm:
        """Bind a form containing *only* this schema's declared fields.

        Used by action modals and filter forms: the schema renders a subset of a
        larger ``ModelForm``, so binding the full form would fail validation on
        fields the user never saw. Goes through :meth:`to_form_class` — the same
        path wizard steps use.
        """
        form_class = self.to_form_class()
        if not issubclass(form_class, ModelForm):
            kwargs.pop("instance", None)
        form = form_class(*args, **kwargs)
        self._attach_image_validators(form)
        return form

    def _attach_image_validators(self, form: BaseForm) -> None:
        specs = self.image_specs()
        if not specs:
            return
        from ..images.specs import ImageSpec
        from ..images.validators import validate_image

        def make_validator(spec: ImageSpec) -> Any:
            def _validate(value: Any) -> None:
                validate_image(value, spec)

            return _validate

        for name, config in specs.items():
            if name not in form.fields:
                continue
            form.fields[name].validators.append(make_validator(ImageSpec.from_field_config(config)))

    def process_images(self, instance: Any) -> None:
        """Run the image pipeline for every FileUpload field. Call after save."""
        from ..images.pipeline import process_image
        from ..images.specs import ImageSpec

        for name, config in self.image_specs().items():
            field_file = getattr(instance, name, None)
            if field_file:
                process_image(field_file, ImageSpec.from_field_config(config))
        instance.save()

    def iter_fields(self) -> Iterator[Component]:
        yield from forms_bridge.iter_fields(self)

    def image_specs(self) -> dict[str, dict[str, Any]]:
        return forms_bridge.image_specs(self)

    # -- rendering ---------------------------------------------------

    def _effective_components(self, form: BaseForm) -> list[Component]:
        if not self._append_unmapped:
            return self._components
        from .fields.text import Hidden, TextInput

        tail: list[Component] = []
        for name in forms_bridge.unmapped_fields(self, form):
            if form.fields[name].widget.is_hidden:
                tail.append(Hidden(name))
            else:
                tail.append(TextInput(name))
        return [*self._components, *tail]

    def render(
        self,
        *,
        request: HttpRequest | None = None,
        form: BaseForm | None = None,
        record: Any | None = None,
        operation: str = "create",
    ) -> SafeString:
        if form is None:
            form = self.build_form(instance=record)
        else:
            forms_bridge.check_alignment(self, form)

        ctx = RenderContext(
            request=request,
            form=form,
            record=record,
            operation=operation,  # type: ignore[arg-type]
        )
        children = [c.render(ctx.child()) for c in self._effective_components(form)]

        data = {
            # each child is a SafeString from Component.render
            "children_html": mark_safe("".join(str(c) for c in children)),  # noqa: S308
            "hidden_html": [str(bf) for bf in form.hidden_fields()],
            "non_field_errors": list(form.non_field_errors()),
        }
        return SafeString(render_to_string(self.template_name, data, request=request))

    def render_form(
        self,
        *,
        request: HttpRequest | None = None,
        form: BaseForm | None = None,
        record: Any | None = None,
        action: str = "",
        submit_label: str = "Save",
        show_actions: bool = True,
    ) -> SafeString:
        form = form or self.build_form(instance=record)
        schema_html = self.render(request=request, form=form, record=record)
        data = {
            "schema_html": schema_html,
            "method": "post",
            "enctype": "multipart/form-data" if form.is_multipart() else "",
            "action": action,
            "submit_label": submit_label,
            "show_actions": show_actions,
        }
        return SafeString(
            render_to_string("django_cotton_components/form.html", data, request=request)
        )
