# Settings & install

## Install

```bash
pip install "django-control-components[images]"        # + Pillow for image fields
pip install "django-control-components[wizard]"        # + django-formtools for wizards
pip install "django-control-components[studio]"        # + django-control-components-studio (no-code builder)
```

```python
INSTALLED_APPS = [
    # ...
    "django_cotton",  # BEFORE django_control_components
    "django_control_components",
    "django_control_components.studio",  # only for the no-code seam
]
```

`django_cotton` **must** come before `django_control_components`. A system check
enforces it (below).

### Assets

Add to your base template `<head>`:

```django
{% load dcc_tags %}
{% dcc_assets %}
```

It emits, **in this order**: `dcc.css`, the icon-set `<link>`, htmx, `dcc.js`,
the `@alpinejs/focus` plugin, Alpine. The order matters — `dcc.js` registers an
`alpine:init` listener before Alpine scans the DOM, and the focus plugin must
load before Alpine core (`x-trap` in modals/drawers).

Pass `False` for anything the host page already loads — and then **you** own the
ordering:

```django
{% dcc_assets htmx=False alpine=False %}   {# you load them, in the right order #}
{% dcc_assets focus=False %}                {# you load @alpinejs/focus yourself #}
```

For the no-code studio builder page, also add `{% dcc_studio_assets %}` (after
`{% dcc_assets %}`).

### URLs

Mount the internal endpoints once:

```python
# config/urls.py
urlpatterns = [
    path("dcc/", include("django_control_components.urls")),
    # ...
]
```

This adds `dcc:action` (`a/<owner_key>/<action_name>/`) and `dcc:schema-validate`
(`v/<schema_key>/`). The literal prefix is your choice; URL reversing uses the
`dcc` namespace, so only mounting it once matters.

## The `DCC` dict

All configuration is one dict in your Django settings. Read it through the
`dcc_settings` shim so a **typo raises** instead of silently returning `None`
(`conf.py:39-44`) — `dcc_settings.NOSUCH` → `AttributeError("Unknown DCC
setting: 'NOSUCH'. Valid keys: [...]")`.

```python
DCC = {
    "TABLE_CLIENT_SIDE_MAX_ROWS": 200,
    "TABLE_PER_PAGE_CHOICES": [10, 25, 50, 100],
    "LIVE_VALIDATION_DEBOUNCE_MS": 400,
    "IMAGE_MAX_PIXELS": 24_000_000,
    "THUMBNAIL_BACKEND": None,
    "URL_PREFIX": "dcc/",
    "ICON_SET": "django_control_components.icons.FontAwesome",
    "ICON_ASSET_URL": "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.7.2/css/all.min.css",
    "STUDIO_MODELS": [],
}
```

| Key | Type | Default | What reads it / what breaks if wrong |
|---|---|---|---|
| `TABLE_CLIENT_SIDE_MAX_ROWS` | int | `200` | `Table._resolve_mode` — at or below this row count a table renders client-side (zero background requests). Too high → huge DOM; too low → server round-trips for small tables. |
| `TABLE_PER_PAGE_CHOICES` | list[int] | `[10, 25, 50, 100]` | `Table.per_page_choices` fallback. Only the **first** value is used as the page size unless the table calls `.paginate([...])` (which then also renders the "Rows" picker in server mode). |
| `LIVE_VALIDATION_DEBOUNCE_MS` | int | `400` | `Field.live()` default debounce for the per-field validate round-trip. |
| `IMAGE_MAX_PIXELS` | int | `24_000_000` | `validate_image` — sets `PIL.Image.MAX_IMAGE_PIXELS` and promotes `DecompressionBombWarning` to an error **before** decode. Lower = stricter bomb guard. |
| `THUMBNAIL_BACKEND` | dotted path \| `None` | `None` | `get_thumbnail_backend()`. `None` → probe `easy_thumbnails`, then fall back to `PillowThumbnailBackend`. A bad path raises `ThumbnailBackendError`. |
| `URL_PREFIX` | str | `"dcc/"` | The intended mount prefix for the internal endpoints. Reversing uses the `dcc` namespace, so this is documentation more than enforcement — but keep your `include(...)` prefix in sync. |
| `ICON_SET` | dotted path | `…icons.FontAwesome` | `icons.active_set()` — the class rendering `{% dcc_icon %}` / every component icon. Must satisfy the `IconSet` protocol. |
| `ICON_ASSET_URL` | str \| `None` | FontAwesome 6.7.2 CDN CSS | The `<link>` `{% dcc_assets %}` emits for icons. `None` → the set self-hosts / emits nothing. |
| `STUDIO_MODELS` | list[str] | `[]` | `"app_label.Model"` entries a stored studio spec or a widget `.query({...})` may aggregate over. A model not in this list is refused. |
| `VENDOR_ASSETS` | bool | `False` | `{% dcc_assets %}` — `True` serves htmx / Alpine / focus from your own static files instead of jsDelivr. Run `manage.py dcc_vendor_assets --dest <static dir>` to fetch the pinned files first. Air-gapped and privacy-sensitive deploys. |
| `VENDOR_ASSET_DIR` | str | `"dcc/vendor/"` | Static path prefix the vendored copies are served from when `VENDOR_ASSETS`. |
| `ASSET_SRI` | dict[str, str] | `{}` | `{cdn_url: "sha384-…"}`. Any CDN asset URL present is emitted with `integrity` + `crossorigin="anonymous"`. Ignored for a URL served via `VENDOR_ASSETS`. |

Alpine is pinned exactly (`ALPINE_VERSION` in `templatetags/dcc_tags.py`), not a
floating `3.x.x` range — bump it deliberately, in lockstep with the vendored files.

### Live re-read

`dcc_settings` reads `settings.DCC` on **every** access — no process restart
needed for a change to take effect. The icon registry memoises its resolved set,
but a `setting_changed` receiver clears that cache, so
`@override_settings(DCC=...)` in tests works.

## System checks

`manage.py check` reports:

| id | level | condition |
|---|---|---|
| `django_control_components.E001` | Error | `django_cotton` is not in `INSTALLED_APPS` |
| `django_control_components.W002` | Warning | no `django.template.backends.django.DjangoTemplates` backend in `TEMPLATES` — component rendering (`render_to_string`) will fail |
| `django_control_components.E010` | Error | `DCC` contains an unknown key (a typo — the shim would raise on first access) |
| `django_control_components.E011` | Error | `DCC["ICON_SET"]` cannot be imported |
| `django_control_components.W011` | Warning | a `DCC["STUDIO_MODELS"]` / `STUDIO_RESOURCE_MODELS` label does not resolve to a model |
| `django_control_components.W012` | Warning | a `DCC["STUDIO_CALLABLES"]` dotted path cannot be imported |
| `dcc_studio.E001` | Error | `django_control_components.studio` is installed without `django_control_components` |

## Styling

Components emit semantic `dcc-*` classes and ship a dependency-free stylesheet
(`css/dcc.css` — design tokens as CSS custom properties, light/dark aware). To
theme or purge with Tailwind 4, point a build at `css/dcc.css` instead of loading
the prebuilt file.
