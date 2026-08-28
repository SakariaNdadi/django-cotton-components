# Demo project

A complete app that exercises every builder — schema forms, an auto client/server
data table, row & bulk actions, a htmx wizard, panels with widgets and a custom
page, and a **no-code** resource defined entirely from stored JSON.

```bash
# from the repo root
uv sync
uv run --project example python example/manage.py migrate
uv run --project example python example/manage.py seed --fresh
uv run --project example python example/manage.py runserver
```

Open <http://127.0.0.1:8000/>. The dashboard links every feature. Sign in for the
panel — seeded superuser is **demo / demo**.

## What to try

| Page | What it shows |
|---|---|
| **Dashboard** `/` | Feature hub + KPI tiles |
| **Component gallery** `/components/` | Every primitive: buttons, badges, icons, modal, menu, all form controls |
| **Articles table** `/articles/` | Status / Featured filters, search, sort, pagination — all zero-request at 60 rows. Tick rows → bulk bar → **"Mark live"** confirm modal → toast + refresh; **"Select every matching row"** for bulk over the whole filter. Row actions: **Edit** (navigates), **Quick edit** (schema form in a modal), **Toggle ★** (inline). |
| **New / Edit article** `/articles/new/` | Sections, **searchable** selects, `published_at` appears only when Status = Live, Pillow-validated image upload. Submit with JavaScript disabled — still validates. |
| **Publish wizard** `/wizard/` | Steps advance over **htmx** (no full-page reload); per-step Django validation; `Back` and no-JS still work. |
| **Panel** `/panel/` | Dashboard with **stat / chart / table widgets**; a custom **Reports** page (`Panel.pages`); Article & Author resources with list · create · edit · view · **delete** and a declared **infolist** on the view page. |
| **Comments (no-code)** `/panel/d/comments/` | A full resource — table, form, infolist — defined by one stored `DashboardSpec` JSON row. No Python subclass. |
| **Django admin** `/admin/` | Same credentials; runs alongside the panel, untouched |

## Seed flags

- `--fresh` — wipe demo data first
- `--big 60000` — bulk rows so the articles table flips to **server-side streaming**
  (keyset cursor, no `COUNT(*)`, append-on-scroll)
- `--no-images` — skip avatar / cover generation (faster)

## Large-dataset mode

`--big 60000` (or lowering `DCC["TABLE_CLIENT_SIDE_MAX_ROWS"]` in
`example/config/settings.py`) switches `/articles/` to server mode: the first page
renders, then a sentinel row appends the next batch as you scroll. Watch the query
log — there is no `SELECT COUNT(*)`.
