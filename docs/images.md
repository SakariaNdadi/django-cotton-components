# Images

## Mental model

Validation and processing for uploaded images, driven off a `FileUpload` schema
field. Needs Pillow (`pip install "django-control-components[images]"`).

Two phases, at two different times:

1. **Validate** — during the Django form's `clean()`. The schema attaches an
   image validator to the Django field. A failure is a normal form error
   (`ImageValidationError` is a `django.core.exceptions.ValidationError`
   subclass), never a 500.
2. **Process** — after `form.save()`. `schema.process_images(instance)` runs
   resize → convert → strip-EXIF for every `FileUpload` field and re-saves the
   instance. `SchemaFormMixin` and panel resources call this for you.

The validator **never trusts the file extension or the browser `Content-Type`**
— it sniffs the content and decodes with Pillow (`images/validators.py:1-6`). The
`.accept(...)` setter is a client-side `<input accept>` hint only; it is **not**
enforced server-side.

## Quick start

```python
from django_control_components.schemas import FileUpload

FileUpload.make("cover")
    .image()
    .accept("image/png,image/jpeg,image/webp")   # client hint only
    .max_size("2mb")
    .min_dimensions(600, 315)
    .max_dimensions(4000, 4000)
    .aspect_ratio("16:9")           # default tolerance ±2%
    .aspect_tolerance(0.05)         # widen to ±5%
    .resize(max_width=1600)         # downscale on save, keep aspect
    .convert("webp", quality=82)    # re-encode
    .strip_exif()                   # default ON — drops orientation/GPS
```

## `FileUpload` setters

| setter | phase | effect |
|---|---|---|
| `.image(value=True)` | both | marks this an image field; sets the default `accept` to `image/*` |
| `.accept(str)` | client only | the `<input accept="…">` attribute — a hint, never validated |
| `.max_size("2mb" \| bytes)` | validate | reject larger files (units: `b`, `k`/`kb`, `m`/`mb`) |
| `.min_dimensions(w, h)` / `.max_dimensions(w, h)` | validate | pixel bounds |
| `.aspect_ratio("16:9" \| float)` | validate | required width/height ratio |
| `.aspect_tolerance(fraction)` | validate | allowed deviation from `aspect_ratio` (default `0.02`) |
| `.resize(*, max_width=None, max_height=None)` | process | aspect-preserving downscale (never upscales) |
| `.convert(fmt, *, quality=82)` | process | re-encode to `fmt`; `quality` applies to JPEG/WEBP |
| `.strip_exif(value=True)` | process | **default on** — see below |
| `.allow_svg(value=True)` | validate | accept SVG uploads (see below) |

`.image_spec()` collects these keys into a dict; `ImageSpec.from_field_config`
turns that into an `ImageSpec` dataclass.

## Validation — `validate_image(file, spec) -> (width, height)`

Order of checks (`images/validators.py`):

1. **`max_size`** — before anything else, including SVG.
2. **SVG** — if the first 1 KB contains `<svg` or `<?xml`:
   - without `.allow_svg()` → `ImageValidationError` (script-injection risk).
   - with `.allow_svg()` → accepted **as-is** and returns `(0, 0)`; Pillow cannot
     decode SVG so the dimension / aspect checks are skipped. **This library does
     not sanitise SVGs** — serve them as downloads, never inline from a trusted
     origin.
3. **Decompression-bomb ceiling** — `Image.MAX_IMAGE_PIXELS` is set to
   `DCC["IMAGE_MAX_PIXELS"]` (default 24 MP) and `DecompressionBombWarning` is
   promoted to an error *before* decode, so the allocation never happens.
4. **Decode** with Pillow — an undecodable file is "File is not a valid image."
5. **`min_dimensions` / `max_dimensions` / `aspect_ratio`** (within
   `aspect_tolerance`).

Returns `(width, height)` on success (`(0, 0)` for an allowed SVG).

## Processing — `process_image(field_file, spec)`

Runs on `form.save()` via `schema.process_images(instance)`.

- No-ops unless the field file exists **and** at least one of
  `resize` / `convert` / `strip_exif` is truthy. Because `strip_exif` defaults
  **`True`**, a plain `.image()` field **re-encodes every upload** even with no
  `.resize()` / `.convert()`.
- `ImageOps.exif_transpose` is always applied first (phone photos come out
  upright), then the rest of the EXIF block — including GPS — is dropped.
- `resize` → `image.thumbnail((max_w or width, max_h or height))` — downscale
  only, aspect preserved.
- `convert` → output format is `convert["format"]`, else the original format,
  else PNG. JPEG output from an RGBA/palette image is flattened to RGB. The file
  gets a new extension **only** when `convert["format"]` is set; a bare
  `.convert()`-less re-encode keeps the name.
- `field_file.save(name, ..., save=False)` — the caller persists the instance
  (`process_images` calls `instance.save()` at the end).

## Thumbnails

```python
from django_control_components.tables import ImageColumn

ImageColumn.make("cover").thumbnail((48, 48)).rounded()
```

or directly:

```python
from django_control_components.images import get_thumbnail_backend

url = get_thumbnail_backend().thumbnail(instance.cover, 48, 48)
```

### `ThumbnailBackend` protocol

```python
class ThumbnailBackend(Protocol):
    def thumbnail(self, field_file, width: int, height: int) -> str: ...
```

- `DCC["THUMBNAIL_BACKEND"]` set → that dotted path is imported and called. An
  `ImportError` raises `ThumbnailBackendError` (the only thing that raises it).
- Not set → the resolver probes for `easy_thumbnails` **first** (using it if
  installed, with `crop=True` — an exact WxH crop), otherwise falls back to
  `PillowThumbnailBackend` (aspect-preserving *fit*, always WEBP quality 80,
  written next to the original as `<name>.dcc<w>x<h>.webp`, generated once and
  cached by that derived name).

So the crop-vs-fit behaviour and the output format differ by which backend is
active — pin `THUMBNAIL_BACKEND` if you need one specific behaviour.

## `ImageSpec`

The low-level frozen dataclass (`images/specs.py:33-58`): `is_image`, `max_size`,
`min_dimensions`, `max_dimensions`, `aspect_ratio`, `aspect_tolerance` (0.02),
`resize`, `convert`, `strip_exif` (True), `allow_svg` (False). Helpers:
`parse_size("5MB")`, `parse_ratio("16:9")`. Primitives: `validate_image(file,
spec)`, `process_image(field_file, spec)`.

## Settings

| Key | Default | Effect |
|---|---|---|
| `IMAGE_MAX_PIXELS` | `24_000_000` | decompression-bomb ceiling, enforced before decode |
| `THUMBNAIL_BACKEND` | `None` | dotted path to a `ThumbnailBackend`; `None` → probe easy_thumbnails, then Pillow |

## Constraints / do not combine

- `.allow_svg()` bypasses dimension and aspect checks (Pillow can't read SVG) but
  **not** `.max_size()` — that is enforced first.
- `.aspect_tolerance(...)` only has an effect alongside `.aspect_ratio(...)`.
- `.resize()` never upscales — a smaller source stays small.
- A `FileUpload` field without `.image()` skips image validation entirely (it is
  just a file input).

## Known sharp edges

- Because `strip_exif` is on by default, uploading a PNG through a bare
  `.image()` field still round-trips it through Pillow on save.
- `ImageColumn.thumbnail(...)` in a table swallows any backend exception and
  falls back to the original image URL — a misconfigured backend fails silently
  there, but `get_thumbnail_backend()` called directly still raises
  `ThumbnailBackendError` on an import failure.
- `validate_image` reads the whole file to decode it; very large *valid* images
  under the pixel ceiling are still fully loaded into memory during `clean()`.
