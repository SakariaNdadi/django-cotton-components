from __future__ import annotations


class DCCError(Exception):
    """Base class for every error raised by this library."""


class SchemaError(DCCError):
    """A schema is misconfigured (unknown field, bad container nesting, ...)."""


class ThumbnailBackendError(DCCError):
    """The dotted path in ``DCC["THUMBNAIL_BACKEND"]`` could not be imported."""
