# Demo project

A small but complete app that exercises every builder: a dashboard, a
schema-driven form, an auto client/server data table with row + bulk actions,
a multi-step wizard, and an admin-style panel with two resources.

```bash
# from the repo root
uv sync
uv run --project example python example/manage.py migrate
uv run --project example python example/manage.py seed --fresh
uv run --project example python example/manage.py runserver
```

Open <http://127.0.0.1:8000/>.

| What | Where | Notes |
|---|---|---|
| Dashboard | `/` | KPI tiles + recent activity |
| Articles table | `/articles/` | 60 rows → client-side (zero requests). Sort / search / paginate locally; filters round-trip; row "Edit" + "Toggle ★"; bulk "Mark live" / "Archive" with confirm modal + toast |
| Schema form | `/articles/new/` | Sections, conditional `published_at` (compiled to Alpine), Pillow image field |
| Wizard | `/wizard/` | Two steps, session-backed, per-step Django validation |
| Panel | `/panel/article/` | Sign in first — seeded superuser is **demo / demo** |
| Django admin | `/admin/` | Same credentials; runs alongside the panel, untouched |

Seed flags:

- `--fresh` wipes demo data first
- `--big 60000` adds bulk rows so the articles table flips to **server-side** htmx
- `--no-images` skips avatar / cover generation (faster)
