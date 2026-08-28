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
                ("Dashboard", "demo:index", "gauge-high", {"index"}),
            ],
        ),
        (
            "Content",
            [
                ("Articles", "demo:article-list", "table-list", {"article-list", "article-edit"}),
                ("New article", "demo:article-create", "plus", {"article-create"}),
                ("Publish wizard", "demo:wizard", "list-check", {"wizard"}),
                ("Component gallery", "demo:components", "shapes", {"components"}),
            ],
        ),
        (
            "Admin panel",
            [
                ("Panel dashboard", "dcc-panel-admin:index", "gauge-high", set()),
                ("Articles resource", "dcc-panel-admin:article-list", "table-cells", set()),
                ("Authors resource", "dcc-panel-admin:author-list", "user", set()),
                ("Reports (custom page)", "dcc-panel-admin:page-reports", "chart-column", set()),
                ("Django admin", "admin:index", "lock", set()),
            ],
        ),
    ]
    return {"demo_nav": nav, "demo_current": current}
