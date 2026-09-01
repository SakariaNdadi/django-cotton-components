"""Introspect a declarative type into UI-form metadata.

The studio palette needs, per registered type: a human label, an icon, a
category, whether it nests children, and - per ``@setter`` - a control kind, a
default, whether it is required, any fixed choices, and a one-line help string.

``Column`` / ``Filter`` / ``Widget`` / ``Action`` are **not** ``Component``
subclasses and each re-implements the ``@setter`` kwargs machinery, so this is a
free function keyed on a class, never a method on a base.
"""

from __future__ import annotations

import inspect
import re
import types
from dataclasses import dataclass
from functools import cache
from typing import Any, Literal, Union, get_args, get_origin

#: setters that take a runtime callable / predicate - never expressible in a
#: stored JSON spec. This module owns the canonical set; ``studio.deserialize``
#: re-exports it under its old private name for one release.
CODE_ONLY_SETTERS = frozenset(
    {"state", "state_fn", "action", "callback", "authorize", "visible", "hidden"}
)

SetterKind = Literal[
    "string", "number", "boolean", "choice", "list", "keyvalue", "object", "unknown"
]

_UNION_TYPES = (Union, types.UnionType)


@dataclass(frozen=True)
class SetterInfo:
    name: str
    kind: SetterKind
    default: Any = None
    required: bool = False
    choices: tuple[tuple[str, str], ...] | None = None
    help: str = ""
    #: takes a runtime closure - surfaced in the inspector but not editable
    code_only: bool = False
    #: privilege gate ("superuser") - stripped from the palette for others
    requires: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "default": self.default,
            "required": self.required,
            "choices": [list(choice) for choice in self.choices] if self.choices else None,
            "help": self.help,
            "code_only": self.code_only,
            "requires": self.requires,
        }


@dataclass(frozen=True)
class TypeInfo:
    name: str
    label: str
    icon: str = ""
    category: str = ""
    accepts_children: bool = False
    help: str = ""
    setters: tuple[SetterInfo, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "icon": self.icon,
            "category": self.category,
            "accepts_children": self.accepts_children,
            "help": self.help,
            "setters": [setter.as_dict() for setter in self.setters],
        }


def setter_names(cls: type) -> list[str]:
    """The sorted ``@setter``-marked method names on ``cls`` - the same walk
    ``Component._apply_kwargs`` does to validate kwargs, extracted once."""
    return sorted(
        name for name in dir(cls) if getattr(getattr(cls, name, None), "__dcc_setter__", False)
    )


def _first_line(doc: str | None) -> str:
    for line in (doc or "").strip().splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _humanize(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", " ", name)


def _jsonable(value: Any) -> bool:
    return isinstance(value, str | int | float | bool | type(None))


def _unwrap_optional(annotation: Any) -> Any:
    if get_origin(annotation) in _UNION_TYPES:
        non_none = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return annotation


def _classify(annotation: Any) -> tuple[SetterKind, tuple[tuple[str, str], ...] | None, bool]:
    """Map a resolved annotation to ``(kind, choices, code_only)``."""
    if annotation is inspect.Parameter.empty:
        return "string", None, False
    if "Callable" in str(annotation):
        return "unknown", None, True

    annotation = _unwrap_optional(annotation)
    origin = get_origin(annotation)

    if annotation is bool:
        return "boolean", None, False
    if annotation in (int, float):
        return "number", None, False
    if annotation is str:
        return "string", None, False
    if origin is Literal:
        return "choice", tuple((str(arg), str(arg)) for arg in get_args(annotation)), False
    if origin is dict or annotation is dict:
        return "keyvalue", None, False
    if origin in (list, set, frozenset, tuple) or annotation in (list, set, tuple):
        return "list", None, False
    if origin in _UNION_TYPES:
        kinds = {_classify(arg)[0] for arg in get_args(annotation) if arg is not type(None)}
        return (kinds.pop() if len(kinds) == 1 else "string"), None, False
    return "object", None, False


@cache
def _describe_uncached(cls: type) -> TypeInfo:
    setters: list[SetterInfo] = []
    for name in setter_names(cls):
        method = getattr(cls, name)
        resolved = True
        try:
            signature = inspect.signature(method, eval_str=True)
        except (NameError, TypeError, ValueError):
            resolved = False
            try:
                signature = inspect.signature(method, eval_str=False)
            except (TypeError, ValueError):
                setters.append(SetterInfo(name=name, kind="unknown", code_only=True))
                continue

        params = [p for p in signature.parameters.values() if p.name != "self"]
        help_text = _first_line(method.__doc__)
        in_deny = name in CODE_ONLY_SETTERS

        if not params:
            setters.append(
                SetterInfo(
                    name=name, kind="boolean", default=True, help=help_text, code_only=in_deny
                )
            )
            continue

        param = params[0]
        annotation = param.annotation if resolved else inspect.Parameter.empty
        kind, choices, ann_code_only = _classify(annotation)
        has_default = param.default is not inspect.Parameter.empty
        default = param.default if has_default and _jsonable(param.default) else None
        setters.append(
            SetterInfo(
                name=name,
                kind=kind,
                default=default,
                required=not has_default,
                choices=choices,
                help=help_text,
                code_only=in_deny or ann_code_only or not resolved,
            )
        )

    return TypeInfo(
        name=cls.__name__,
        label=_humanize(cls.__name__),
        help=_first_line(cls.__doc__),
        setters=tuple(setters),
    )


def describe_type(cls: type, *, overrides: dict[str, Any] | None = None) -> TypeInfo:
    """``TypeInfo`` for ``cls``, with hand ``overrides`` merged over introspection.

    ``overrides`` keys: ``label``, ``icon``, ``category``, ``accepts_children``,
    ``help``, and ``setters`` (``{setter_name: {field: value, ...}}``).
    """
    info = _describe_uncached(cls)
    if not overrides:
        return info

    setter_overrides: dict[str, dict[str, Any]] = overrides.get("setters", {})
    setters = tuple(
        _apply_setter_overrides(setter, setter_overrides.get(setter.name))
        for setter in info.setters
    )
    return TypeInfo(
        name=info.name,
        label=overrides.get("label", info.label),
        icon=overrides.get("icon", info.icon),
        category=overrides.get("category", info.category),
        accepts_children=overrides.get("accepts_children", info.accepts_children),
        help=overrides.get("help", info.help),
        setters=setters,
    )


def _apply_setter_overrides(setter: SetterInfo, override: dict[str, Any] | None) -> SetterInfo:
    if not override:
        return setter
    choices = override.get("choices")
    return SetterInfo(
        name=setter.name,
        kind=override.get("kind", setter.kind),
        default=override.get("default", setter.default),
        required=override.get("required", setter.required),
        choices=(
            tuple(tuple(choice) for choice in choices) if choices is not None else setter.choices
        ),
        help=override.get("help", setter.help),
        code_only=override.get("code_only", setter.code_only),
        requires=override.get("requires", setter.requires),
    )


def strip_privileged_setters(info: TypeInfo, *, is_superuser: bool) -> TypeInfo:
    """Drop ``requires="superuser"`` setters (e.g. ``Column.allow_html``) so a
    non-superuser's palette cannot even offer them."""
    if is_superuser:
        return info
    kept = tuple(s for s in info.setters if s.requires != "superuser")
    if len(kept) == len(info.setters):
        return info
    return TypeInfo(
        name=info.name,
        label=info.label,
        icon=info.icon,
        category=info.category,
        accepts_children=info.accepts_children,
        help=info.help,
        setters=kept,
    )
