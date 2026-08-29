"""Predicates referenced by alias in studio-callables tests."""

from __future__ import annotations

from typing import Any


def always_true(*args: Any, **kwargs: Any) -> bool:
    return True


def always_false(*args: Any, **kwargs: Any) -> bool:
    return False
