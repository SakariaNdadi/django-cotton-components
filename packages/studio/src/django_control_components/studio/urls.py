"""The standalone studio mount.

    # project urls.py
    path("studio/", include("django_control_components.studio.urls")),

Every builder view lives here under the flat ``dcc_studio`` namespace - the
runtime rendering of stored specs stays on the panel (``Panel.dynamic()``).
"""

from __future__ import annotations

from django.urls import path

from .views import (
    DashboardBuilder,
    DashboardIndex,
    DashboardPreview,
    DashboardSave,
    ModelFieldsApi,
    ModelsApi,
    NavBuilder,
    NavPreview,
    NavSave,
    PaletteApi,
    ResourceBuilder,
    ResourceIndex,
    ResourcePreview,
    ResourceSave,
    RolesView,
    StudioHome,
)

app_name = "dcc_studio"

urlpatterns = [
    path("", StudioHome.as_view(), name="home"),
    path("nav/<str:panel>/", NavBuilder.as_view(), name="nav"),
    path("nav/<str:panel>/save/", NavSave.as_view(), name="nav-save"),
    path("nav/<str:panel>/preview/", NavPreview.as_view(), name="nav-preview"),
    path("dashboards/", DashboardIndex.as_view(), name="dashboards"),
    path("dashboards/<slug:slug>/", DashboardBuilder.as_view(), name="dash"),
    path("dashboards/<slug:slug>/save/", DashboardSave.as_view(), name="dash-save"),
    path("dashboards/<slug:slug>/preview/", DashboardPreview.as_view(), name="dash-preview"),
    path("resources/", ResourceIndex.as_view(), name="resources"),
    path("resources/<slug:slug>/", ResourceBuilder.as_view(), name="resource"),
    path("resources/<slug:slug>/save/", ResourceSave.as_view(), name="resource-save"),
    path("resources/<slug:slug>/preview/", ResourcePreview.as_view(), name="resource-preview"),
    path("roles/", RolesView.as_view(), name="roles"),
    path("api/palette/", PaletteApi.as_view(), name="api-palette"),
    path("api/models/", ModelsApi.as_view(), name="api-models"),
    path("api/models/<str:label>/", ModelFieldsApi.as_view(), name="api-model-fields"),
]
