from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.core.exceptions import ValidationError


class ImageValidationError(ValidationError):
    """Raised when an uploaded file fails image validation."""


_UNITS = {"": 1, "b": 1, "k": 1024, "kb": 1024, "m": 1024**2, "mb": 1024**2}


def parse_size(value: str | int) -> int:
    if isinstance(value, int):
        return value
    text = value.strip().lower()
    for suffix, mult in sorted(_UNITS.items(), key=lambda kv: -len(kv[0])):
        if suffix and text.endswith(suffix):
            return int(float(text[: -len(suffix)]) * mult)
    return int(text)


def parse_ratio(value: str) -> float:
    if ":" in value:
        w, h = value.split(":", 1)
        return float(w) / float(h)
    return float(value)


@dataclass(frozen=True)
class ImageSpec:
    is_image: bool = True
    max_size: int | None = None
    min_dimensions: tuple[int, int] | None = None
    max_dimensions: tuple[int, int] | None = None
    aspect_ratio: float | None = None
    aspect_tolerance: float = 0.02
    resize: dict[str, Any] = field(default_factory=dict)
    convert: dict[str, Any] = field(default_factory=dict)
    strip_exif: bool = True
    allow_svg: bool = False

    @classmethod
    def from_field_config(cls, config: dict[str, Any]) -> ImageSpec:
        return cls(
            is_image=config.get("image", True),
            max_size=parse_size(config["max_size"]) if "max_size" in config else None,
            min_dimensions=config.get("min_dimensions"),
            max_dimensions=config.get("max_dimensions"),
            aspect_ratio=parse_ratio(config["aspect_ratio"]) if "aspect_ratio" in config else None,
            resize=config.get("resize") or {},
            convert=config.get("convert") or {},
            strip_exif=config.get("strip_exif", True),
            allow_svg=config.get("allow_svg", False),
        )
