from __future__ import annotations

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from django_cotton_components.core.exceptions import ThumbnailBackendError
from django_cotton_components.images.backends import (
    PillowThumbnailBackend,
    get_thumbnail_backend,
)
from django_cotton_components.schemas import FileUpload, Schema
from tests.testapp.forms import AuthorForm
from tests.testapp.models import Author

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

pytestmark = pytest.mark.django_db


def _png_upload(name="a.png", size=(80, 80)) -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", size, (10, 20, 30)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@pytest.fixture
def media(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


def _schema() -> Schema:
    return (
        Schema.make()
        .form(AuthorForm)
        .schema([FileUpload.make("avatar").image().min_dimensions(40, 40).convert("webp")])
    )


def test_valid_image_passes_form_validation(media):
    form = _schema().build_form(data={"name": "Ada"}, files={"avatar": _png_upload()})
    assert form.is_valid(), form.errors


def test_too_small_image_fails_form_validation(media):
    form = _schema().build_form(data={"name": "Ada"}, files={"avatar": _png_upload(size=(10, 10))})
    assert not form.is_valid()
    assert "avatar" in form.errors


def test_non_image_fails_form_validation(media):
    bad = SimpleUploadedFile("x.png", b"not an image", content_type="image/png")
    form = _schema().build_form(data={"name": "Ada"}, files={"avatar": bad})
    assert not form.is_valid()


def test_process_images_converts_on_save(media):
    form = _schema().build_form(data={"name": "Ada"}, files={"avatar": _png_upload()})
    assert form.is_valid(), form.errors
    author = form.save()
    _schema().process_images(author)
    author.refresh_from_db()
    assert author.avatar.name.endswith(".webp")


def test_pillow_thumbnail_backend(media):
    author = Author.objects.create(name="Ada")
    author.avatar.save("a.png", _png_upload(), save=True)
    url = PillowThumbnailBackend().thumbnail(author.avatar, 32, 32)
    assert url
    # second call hits the cache branch
    assert PillowThumbnailBackend().thumbnail(author.avatar, 32, 32) == url


def test_pillow_thumbnail_backend_empty_file():
    assert PillowThumbnailBackend().thumbnail(None, 10, 10) == ""


def test_get_thumbnail_backend_default():
    assert isinstance(get_thumbnail_backend(), PillowThumbnailBackend)


def test_get_thumbnail_backend_bad_path(settings):
    settings.DCC = {"THUMBNAIL_BACKEND": "nonexistent.module.Backend"}
    with pytest.raises(ThumbnailBackendError):
        get_thumbnail_backend()
