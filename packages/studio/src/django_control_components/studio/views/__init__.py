"""Studio builder views — mounted by ``django_control_components.studio.urls``."""

from __future__ import annotations

from .api import ModelFieldsApi, ModelsApi, PaletteApi
from .dashboard import (
    DashboardBuilder,
    DashboardIndex,
    DashboardPreview,
    DashboardSave,
)
from .nav import NavBuilder, NavPreview, NavSave, StudioHome
from .resource import ResourceBuilder, ResourceIndex, ResourcePreview, ResourceSave
from .roles import RolesView

__all__ = [
    "DashboardBuilder",
    "DashboardIndex",
    "DashboardPreview",
    "DashboardSave",
    "ModelFieldsApi",
    "ModelsApi",
    "NavBuilder",
    "NavPreview",
    "NavSave",
    "PaletteApi",
    "ResourceBuilder",
    "ResourceIndex",
    "ResourcePreview",
    "ResourceSave",
    "RolesView",
    "StudioHome",
]
