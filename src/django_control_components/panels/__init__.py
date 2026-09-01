from ..core.type_registry import TypeRegistry
from .pages import DashboardPage, PanelPage
from .panel import Panel
from .resource import Resource
from .widgets import BarListWidget, ChartWidget, StatWidget, TableWidget, Widget

WIDGET_TYPES: TypeRegistry[Widget] = TypeRegistry("widget")
for _widget_cls, _label, _icon in (
    (StatWidget, "Stat", "hashtag"),
    (ChartWidget, "Chart", "chart-line"),
    (BarListWidget, "Bar list", "chart-simple"),
    (TableWidget, "Table", "table"),
):
    WIDGET_TYPES.register(_widget_cls, label=_label, icon=_icon, category="widget")

__all__ = [
    "WIDGET_TYPES",
    "BarListWidget",
    "ChartWidget",
    "DashboardPage",
    "Panel",
    "PanelPage",
    "Resource",
    "StatWidget",
    "TableWidget",
    "Widget",
]
