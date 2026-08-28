"""Process a validated image on ``form.save()``.

Synchronous and bounded to one image. EXIF orientation is applied (so phone
photos are upright) and the rest of the EXIF block — including GPS — is dropped.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from django.core.files.base import ContentFile

from .specs import ImageSpec
from .validators import _load_pillow

if TYPE_CHECKING:
    from django.db.models.fields.files import FieldFile

_FORMAT_EXT = {"webp": ".webp", "jpeg": ".jpg", "jpg": ".jpg", "png": ".png"}


def process_image(field_file: FieldFile, spec: ImageSpec) -> None:
    if not field_file or not spec.is_image:
        return
    if not (spec.resize or spec.convert or spec.strip_exif):
        return

    Image = _load_pillow()
    from PIL import ImageOps

    field_file.open()
    try:
        image = Image.open(field_file)
        image.load()
    finally:
        field_file.close()

    image = ImageOps.exif_transpose(image)  # apply orientation, then forget EXIF

    if spec.resize:
        max_w = spec.resize.get("max_width")
        max_h = spec.resize.get("max_height")
        if max_w or max_h:
            image.thumbnail((max_w or image.width, max_h or image.height))

    out_format = str(spec.convert.get("format") or image.format or "PNG").upper()
    save_kwargs: dict[str, int] = {}
    if out_format in ("JPEG", "WEBP"):
        save_kwargs["quality"] = int(spec.convert.get("quality", 82))
        if out_format == "JPEG" and image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format=out_format, **save_kwargs)
    buffer.seek(0)

    name: str = field_file.name or "image"
    if spec.convert.get("format"):
        stem = name.rsplit(".", 1)[0] if "." in name else name
        name = stem + _FORMAT_EXT.get(out_format.lower(), f".{out_format.lower()}")

    field_file.save(name, ContentFile(buffer.read()), save=False)
