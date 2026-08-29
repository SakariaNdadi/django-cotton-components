"""Read-only JSON the builder fetches: the palette and the model pickers."""

from __future__ import annotations

from typing import Any

from django.http import Http404, HttpRequest, JsonResponse

from ..introspect import (
    describe_model,
    installed_models,
    is_sensitive_model,
    resolve_model,
)
from ..palette import palette
from .base import StudioView


class PaletteApi(StudioView):
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        return JsonResponse(palette(request))


class ModelsApi(StudioView):
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        return JsonResponse({"models": installed_models(request)})


class ModelFieldsApi(StudioView):
    def get(self, request: HttpRequest, label: str, *args: Any, **kwargs: Any) -> JsonResponse:
        try:
            model = resolve_model(label)
        except LookupError:
            raise Http404("no such model") from None
        if is_sensitive_model(model):
            raise Http404("model not available")
        user = getattr(request, "user", None)
        if not (user and user.is_superuser) and not (
            user and user.has_perm(f"{model._meta.app_label}.view_{model._meta.model_name}")
        ):
            raise Http404("model not available")
        return JsonResponse({"fields": describe_model(model, request)})
