from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from ...core.component import setter
from .base import Field

if TYPE_CHECKING:
    from ...core.context import RenderContext


class FileUpload(Field):
    template_name = "django_cotton_components/controls/upload.html"
    uses_django_widget = False

    @setter
    def image(self, value: bool = True) -> Self:
        return self._set("image", value)

    @setter
    def accept(self, value: str) -> Self:
        return self._set("accept", value)

    # Image-processing setters — consumed by images.pipeline on form.save().
    @setter
    def max_size(self, value: str | int) -> Self:
        return self._set("max_size", value)

    @setter
    def min_dimensions(self, width: int, height: int) -> Self:
        return self._set("min_dimensions", (width, height))

    @setter
    def max_dimensions(self, width: int, height: int) -> Self:
        return self._set("max_dimensions", (width, height))

    @setter
    def aspect_ratio(self, value: str) -> Self:
        return self._set("aspect_ratio", value)

    @setter
    def resize(self, *, max_width: int | None = None, max_height: int | None = None) -> Self:
        return self._set("resize", {"max_width": max_width, "max_height": max_height})

    @setter
    def convert(self, fmt: str, *, quality: int = 82) -> Self:
        return self._set("convert", {"format": fmt, "quality": quality})

    @setter
    def strip_exif(self, value: bool = True) -> Self:
        return self._set("strip_exif", value)

    @setter
    def allow_svg(self, value: bool = True) -> Self:
        return self._set("allow_svg", value)

    def image_spec(self) -> dict[str, Any]:
        keys = (
            "image",
            "max_size",
            "min_dimensions",
            "max_dimensions",
            "aspect_ratio",
            "resize",
            "convert",
            "strip_exif",
            "allow_svg",
        )
        return {k: self._config[k] for k in keys if k in self._config}

    def get_view_data(self, ctx: RenderContext) -> dict[str, Any]:
        data = super().get_view_data(ctx)
        data["accept"] = self._config.get("accept", "image/*" if "image" in self._config else "*/*")
        current = data["value"]
        data["current_url"] = getattr(current, "url", "") if current else ""
        data["value"] = None
        return data
