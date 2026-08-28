from __future__ import annotations


class DCCError(Exception):
    """Base class for every error raised by this library."""


class SchemaError(DCCError):
    """A schema is misconfigured (unknown field, bad container nesting, ...)."""


class ThumbnailBackendError(DCCError):
    """The configured thumbnail backend could not be loaded or produced no output."""
