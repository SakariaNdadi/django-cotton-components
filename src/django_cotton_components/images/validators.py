"""Content-sniffing validation for uploaded images.

Never trusts the file extension or the browser-supplied ``Content-Type``. A
decompression-bomb guard is set explicitly rather than relying on Pillow's
warning, which does not stop the allocation.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from ..conf import dcc_settings
from .specs import ImageSpec, ImageValidationError

if TYPE_CHECKING:
    from django.core.files import File

_SVG_MARKERS = (b"<svg", b"<?xml")


def _load_pillow() -> Any:  # returns the PIL.Image module
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - exercised only without Pillow
        raise ImageValidationError(
            "Pillow is required for image fields. Install django-cotton-components[images]."
        ) from exc
    return Image


def validate_image(file: File[Any], spec: ImageSpec) -> tuple[int, int]:
    """Validate an uploaded file against ``spec``. Returns ``(width, height)``.

    Raises :class:`ImageValidationError` on any mismatch.
    """
    file.seek(0)
    head = file.read(1024)
    file.seek(0)

    if spec.max_size is not None and file.size > spec.max_size:
        raise ImageValidationError(f"File is larger than {spec.max_size} bytes.")

    if any(marker in head.lower() for marker in _SVG_MARKERS):
        if not spec.allow_svg:
            raise ImageValidationError(
                "SVG uploads are rejected by default (script-injection risk). "
                "Enable .allow_svg() to accept them. SVGs are stored as-is — this "
                "library does not sanitise them, so serve them as downloads, never "
                "inline from a trusted origin."
            )
        # Pillow cannot decode SVG; the size check above is the only guard applied.
        return (0, 0)

    Image = _load_pillow()
    limit = dcc_settings.IMAGE_MAX_PIXELS
    previous = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = limit
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            try:
                probe = Image.open(file)
                probe.verify()
            except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
                raise ImageValidationError("Image exceeds the pixel limit.") from exc
            except ImageValidationError:
                raise
            except Exception as exc:
                raise ImageValidationError("File is not a valid image.") from exc

        file.seek(0)
        image = Image.open(file)
        image.load()
        width, height = image.size
    finally:
        Image.MAX_IMAGE_PIXELS = previous
        file.seek(0)

    if spec.min_dimensions:
        mw, mh = spec.min_dimensions
        if width < mw or height < mh:
            raise ImageValidationError(f"Image must be at least {mw}x{mh}px.")
    if spec.max_dimensions:
        mw, mh = spec.max_dimensions
        if width > mw or height > mh:
            raise ImageValidationError(f"Image must be at most {mw}x{mh}px.")
    if spec.aspect_ratio is not None and height:
        ratio = width / height
        if abs(ratio - spec.aspect_ratio) > spec.aspect_tolerance:
            raise ImageValidationError("Image aspect ratio is out of range.")

    return width, height
