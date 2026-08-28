from __future__ import annotations

from django.urls import resolve


def shell(request):
    try:
        current = resolve(request.path_info).url_name
    except Exception:
        current = None

    nav = [
        (
            "Overview",
            [
                ("Dashboard", "demo:index", "home", {"index"}),
            ],
        ),
        (
            "Content",
            [
                ("Articles", "demo:article-list", "table", {"article-list", "article-edit"}),
                ("New article", "demo:article-create", "plus", {"article-create"}),
                ("Publish wizard", "demo:wizard", "steps", {"wizard"}),
            ],
        ),
        (
            "Admin panel",
            [
                ("Articles resource", "dcc-panel-admin:article-list", "grid", set()),
                ("Django admin", "admin:index", "lock", set()),
            ],
        ),
    ]
    return {"demo_nav": nav, "demo_current": current}
