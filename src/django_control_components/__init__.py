"""Filament-inspired schema, table, and action builders for Django.

The top-level namespace is deliberately import-light: pull builders from their
subpackages (``django_control_components.schemas`` etc.) so importing this package
at module scope never touches the app registry.

``__path__`` is extended so the optional ``django-control-components-studio``
distribution can contribute the ``django_control_components.studio`` subpackage
from its own install location.
"""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

__version__ = "0.0.1"
