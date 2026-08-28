from ..core.type_registry import TypeRegistry
from .pages import DashboardPage, PanelPage
from .panel import Panel
from .resource import Resource
from .widgets import BarListWidget, ChartWidget, StatWidget, TableWidget, Widget

WIDGET_TYPES: TypeRegistry[Widget] = TypeRegistry("widget")
for _w in (StatWidget, ChartWidget, BarListWidget):
    WIDGET_TYPES.register(_w)

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
