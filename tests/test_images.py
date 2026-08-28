from __future__ import annotations

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from django_cotton_components.images.specs import (
    ImageSpec,
    ImageValidationError,
    parse_ratio,
    parse_size,
)
from django_cotton_components.images.validators import validate_image

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402


def _png(width=100, height=100, color=(255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def _upload(content: bytes, name="x.png", content_type="image/png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type=content_type)


def test_parse_helpers():
    assert parse_size("5MB") == 5 * 1024**2
    assert parse_size("500k") == 500 * 1024
    assert parse_size(123) == 123
    assert parse_ratio("16:9") == pytest.approx(16 / 9)


def test_valid_png_passes_and_returns_dimensions():
    w, h = validate_image(_upload(_png(120, 80)), ImageSpec())
    assert (w, h) == (120, 80)


def test_text_file_renamed_to_png_is_rejected():
    with pytest.raises(ImageValidationError, match="not a valid image"):
        validate_image(_upload(b"just some text, not an image", name="evil.png"), ImageSpec())


def test_polyglot_gif_js_rejected():
    payload = b"GIF89a/*<script>alert(1)</script>*/" + b"\x00" * 20
    with pytest.raises(ImageValidationError):
        validate_image(_upload(payload, name="p.gif", content_type="image/gif"), ImageSpec())


def test_svg_rejected_without_allow_svg():
    svg = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><script>x</script></svg>'
    with pytest.raises(ImageValidationError, match="SVG"):
        validate_image(_upload(svg, name="a.svg", content_type="image/svg+xml"), ImageSpec())
    validate_image(_upload(svg, name="a.svg"), ImageSpec(allow_svg=True))


def test_decompression_bomb_rejected(settings):
    settings.DCC = {"IMAGE_MAX_PIXELS": 1000}
    with pytest.raises(ImageValidationError, match="pixel limit"):
        validate_image(_upload(_png(200, 200)), ImageSpec())


def test_dimension_and_ratio_rules():
    with pytest.raises(ImageValidationError, match="at least"):
        validate_image(_upload(_png(10, 10)), ImageSpec(min_dimensions=(50, 50)))
    with pytest.raises(ImageValidationError, match="aspect ratio"):
        validate_image(_upload(_png(100, 100)), ImageSpec(aspect_ratio=parse_ratio("16:9")))


def test_max_size_rule():
    with pytest.raises(ImageValidationError, match="larger than"):
        validate_image(_upload(_png(300, 300)), ImageSpec(max_size=50))


@pytest.mark.django_db
def test_pipeline_strips_exif_and_converts(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    from django.core.files.base import ContentFile

    from django_cotton_components.images.pipeline import process_image
    from tests.testapp.models import Author

    # build a JPEG carrying a GPS EXIF tag
    exif = Image.Exif()
    exif[0x8825] = {1: "N"}  # GPSInfo
    buf = io.BytesIO()
    Image.new("RGB", (60, 40), (0, 128, 0)).save(buf, format="JPEG", exif=exif)

    author = Author.objects.create(name="X")
    author.avatar.save("a.jpg", ContentFile(buf.getvalue()), save=True)

    process_image(author.avatar, ImageSpec(convert={"format": "webp"}, strip_exif=True))
    author.avatar.open()
    out = Image.open(author.avatar)
    assert out.format == "WEBP"
    assert not dict(out.getexif())
