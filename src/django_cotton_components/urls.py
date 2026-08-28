"""Internal endpoints for htmx-driven interactions.

Mount once in the project urlconf::

    path("dcc/", include("django_cotton_components.urls")),
"""

from __future__ import annotations

from django.urls import path

from .actions.endpoints import ActionView
from .schemas.endpoints import SchemaValidateView

app_name = "dcc"

urlpatterns = [
    path("a/<str:owner_key>/<str:action_name>/", ActionView.as_view(), name="action"),
    path("v/<str:schema_key>/", SchemaValidateView.as_view(), name="schema-validate"),
]
