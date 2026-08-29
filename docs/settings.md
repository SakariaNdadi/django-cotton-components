# Settings & install

## Install

```bash
pip install "django-cotton-components[images]"        # + Pillow for image fields
pip install "django-cotton-components[wizard]"        # + django-formtools for wizards
```

```python
INSTALLED_APPS = [
    # ...
    "django_cotton",                       # BEFORE django_cotton_components
    "django_cotton_components",
    "django_cotton_components.studio",     # only for the no-code seam
]
```

`django_cotton` **must** come before `django_cotton_components`. A system check
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
    path("dcc/", include("django_cotton_components.urls")),
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
    "ICON_SET": "django_cotton_components.icons.FontAwesome",
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

### Live re-read

`dcc_settings` reads `settings.DCC` on **every** access — no process restart
needed for a change to take effect. The icon registry memoises its resolved set,
but a `setting_changed` receiver clears that cache, so
`@override_settings(DCC=...)` in tests works.

## System checks

`manage.py check` reports:

| id | level | condition |
|---|---|---|
| `django_cotton_components.E001` | Error | `django_cotton` is not in `INSTALLED_APPS` |
| `django_cotton_components.W002` | Warning | no `django.template.backends.django.DjangoTemplates` backend in `TEMPLATES` — component rendering (`render_to_string`) will fail |

## Styling

Components emit semantic `dcc-*` classes and ship a dependency-free stylesheet
(`css/dcc.css` — design tokens as CSS custom properties, light/dark aware). To
theme or purge with Tailwind 4, point a build at `css/dcc.css` instead of loading
the prebuilt file.
