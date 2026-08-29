from ..core.component import Component
from ..core.type_registry import TypeRegistry
from .fields.boolean import Checkbox, Toggle
from .fields.choice import MultiSelect, Radio, Select
from .fields.file import FileUpload
from .fields.text import EmailInput, Hidden, PasswordInput, Textarea, TextInput
from .layout import Fieldset, Grid, Section, Tab, Tabs
from .schema import Schema

#: field + layout types a stored schema spec may name
FIELD_TYPES: TypeRegistry[Component] = TypeRegistry("field")

for _field_cls, _label, _icon in (
    (TextInput, "Text", "font"),
    (EmailInput, "Email", "envelope"),
    (Hidden, "Hidden", "eye-slash"),
    (Textarea, "Text area", "align-left"),
    (PasswordInput, "Password", "key"),
    (Checkbox, "Checkbox", "square-check"),
    (Toggle, "Toggle", "toggle-on"),
    (Select, "Select", "caret-down"),
    (MultiSelect, "Multi-select", "list-check"),
    (Radio, "Radio group", "circle-dot"),
    (FileUpload, "File upload", "upload"),
):
    FIELD_TYPES.register(_field_cls, label=_label, icon=_icon, category="field")

for _layout_cls, _label, _icon in (
    (Section, "Section", "square"),
    (Grid, "Grid", "table-cells"),
    (Fieldset, "Fieldset", "object-group"),
    (Tab, "Tab", "folder"),
    (Tabs, "Tabs", "folder-tree"),
):
    FIELD_TYPES.register(
        _layout_cls, label=_label, icon=_icon, category="layout", accepts_children=True
    )

__all__ = [
    "FIELD_TYPES",
    "Checkbox",
    "EmailInput",
    "Fieldset",
    "FileUpload",
    "Grid",
    "Hidden",
    "MultiSelect",
    "PasswordInput",
    "Radio",
    "Schema",
    "Section",
    "Select",
    "Tab",
    "Tabs",
    "TextInput",
    "Textarea",
    "Toggle",
]
