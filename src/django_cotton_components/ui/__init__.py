"""Canonical UI primitives.

One Python component + one leaf template per primitive. Every other subsystem
(tables, actions, wizards, panels) composes these instead of hand-writing
``<button>`` / ``<span class="dcc-badge">`` markup.
"""

from .badge import Badge
from .button import Button, IconButton
from .checkbox import Checkbox
from .icon import Icon
from .menu import Menu
from .modal import Modal

__all__ = ["Badge", "Button", "Checkbox", "Icon", "IconButton", "Menu", "Modal"]
