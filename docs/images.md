# Images

Validation and processing for uploaded images, driven off a `FileUpload` schema
field. Needs Pillow (`pip install "django-cotton-components[images]"`).

```python
from django_cotton_components.schemas import FileUpload

FileUpload.make("cover")
    .image()
    .accept("image/png,image/jpeg,image/webp")
    .max_size("2mb")
    .min_dimensions(600, 315)
    .max_dimensions(4000, 4000)
    .aspect_ratio("16:9")          # ±2% tolerance
    .resize(max_width=1600)        # downscale on save, keep aspect
    .convert("webp", quality=82)   # re-encode
    .strip_exif()                  # default on — drops orientation/GPS
```

## Two phases

1. **Validate** (form clean). The schema attaches an image validator to the
   Django field: MIME/extension, decode with Pillow, size, dimensions, aspect
   ratio. A failure is a normal form error, not a 500. A decompression-bomb
   ceiling (`DCC["IMAGE_MAX_PIXELS"]`, default 24 MP) is enforced first.

2. **Process** (after save). Call `schema.process_images(instance)` in your
   `form_valid` / resource save hook — it runs `resize` → `convert` →
   `strip_exif` for every `FileUpload` field and re-saves the instance.
   `SchemaFormMixin` and panel resources do this for you.

## Thumbnails

`ImageColumn.make("cover").thumbnail((48, 48)).rounded()` in a table, or call the
backend directly:

```python
from django_cotton_components.images import get_thumbnail_backend
url = get_thumbnail_backend().thumbnail(instance.cover, 48, 48)
```

The default `PillowThumbnailBackend` writes a derivative next to the original on
first request. Point `DCC["THUMBNAIL_BACKEND"]` at your own dotted path to use
sorl / imagekit / a CDN.

## `ImageSpec`

The low-level dataclass (`is_image`, `max_size`, `min_dimensions`,
`max_dimensions`, `aspect_ratio`, `aspect_tolerance`, `resize`, `convert`,
`strip_exif`, `allow_svg`). `FileUpload` builds one; `validate_image(file, spec)`
and `process_image(field_file, spec)` are the primitives.

## Settings

```python
DCC = {
    "IMAGE_MAX_PIXELS": 24_000_000,
    "THUMBNAIL_BACKEND": None,   # None → auto-detect Pillow
}
```
