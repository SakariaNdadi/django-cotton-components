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
for _t in (
    TextInput,
    EmailInput,
    Hidden,
    Textarea,
    PasswordInput,
    Checkbox,
    Toggle,
    Select,
    MultiSelect,
    Radio,
    FileUpload,
    Section,
    Grid,
    Fieldset,
    Tab,
    Tabs,
):
    FIELD_TYPES.register(_t)

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
