from __future__ import annotations

import io
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.module_loading import import_string

from ..conf import dcc_settings
from ..core.exceptions import ThumbnailBackendError
from .validators import _load_pillow

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile


@runtime_checkable
class ThumbnailBackend(Protocol):
    def thumbnail(self, field_file: FieldFile, width: int, height: int) -> str:
        """Return a URL for a ``width``x``height`` thumbnail of ``field_file``."""


class PillowThumbnailBackend:
    """Zero-dependency default. Generates once on write, caches by derived name."""

    def thumbnail(self, field_file: FieldFile, width: int, height: int) -> str:
        if not field_file or not field_file.name:
            return ""
        base = field_file.name.rsplit(".", 1)[0]
        cache_name = f"{base}.dcc{width}x{height}.webp"
        if not default_storage.exists(cache_name):
            Image = _load_pillow()
            field_file.open()
            try:
                image = Image.open(field_file)
                image.load()
            finally:
                field_file.close()
            image.thumbnail((width, height))
            buffer = io.BytesIO()
            image.save(buffer, format="WEBP", quality=80)
            buffer.seek(0)
            default_storage.save(cache_name, ContentFile(buffer.read()))
        return default_storage.url(cache_name)


class EasyThumbnailsBackend:  # pragma: no cover - optional dependency
    def thumbnail(self, field_file: FieldFile, width: int, height: int) -> str:
        from easy_thumbnails.files import get_thumbnailer  # type: ignore[import-not-found]

        thumb = get_thumbnailer(field_file).get_thumbnail({"size": (width, height), "crop": True})
        return str(thumb.url)


def get_thumbnail_backend() -> ThumbnailBackend:
    configured = dcc_settings.THUMBNAIL_BACKEND
    if configured:
        try:
            backend: ThumbnailBackend = import_string(configured)()
        except ImportError as exc:
            raise ThumbnailBackendError(f"Cannot import THUMBNAIL_BACKEND {configured!r}") from exc
        return backend

    try:
        import easy_thumbnails  # type: ignore[import-not-found] # noqa: F401

        return EasyThumbnailsBackend()
    except ImportError:
        return PillowThumbnailBackend()
