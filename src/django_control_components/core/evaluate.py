from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from .exceptions import DCCError

if TYPE_CHECKING:
    from collections.abc import Callable

    from .context import RenderContext

INJECTABLE = frozenset(
    {
        "record",
        "request",
        "user",
        "state",
        "get",
        "set",
        "form",
        "component",
        "context",
        "operation",
    }
)

# Cache parameter names per code object. Code objects are hashable and stable;
# caching the function itself would pin closure cells in memory.
_PARAM_CACHE: dict[Any, frozenset[str]] = {}


class ClosureInjectionError(DCCError):
    """A configuration closure asked for a parameter name that is not injectable."""


def _param_names(fn: Callable[..., Any]) -> frozenset[str]:
    code = getattr(fn, "__code__", None)
    if code is None:  # builtins, callables without __code__
        try:
            sig = inspect.signature(fn)
        except (TypeError, ValueError):
            return frozenset()
        return frozenset(sig.parameters)
    cached = _PARAM_CACHE.get(code)
    if cached is None:
        sig = inspect.signature(fn)
        cached = frozenset(
            name
            for name, p in sig.parameters.items()
            if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
        )
        _PARAM_CACHE[code] = cached
    return cached


def evaluate(value: Any, ctx: RenderContext, *, component: Any = None) -> Any:
    """Resolve a possibly-callable configuration value against a render context.

    Non-callables (and classes) pass straight through. Callables are invoked with
    only the injectable parameters they declare, by name.
    """
    if not callable(value) or isinstance(value, type):
        return value

    params = _param_names(value)
    unknown = params - INJECTABLE
    if unknown:
        raise ClosureInjectionError(
            f"{value!r} requests {sorted(unknown)}; injectable names are {sorted(INJECTABLE)}"
        )

    kwargs: dict[str, Any] = {}
    for name in params:
        kwargs[name] = component if name == "component" else ctx.resolve(name)
    return value(**kwargs)
