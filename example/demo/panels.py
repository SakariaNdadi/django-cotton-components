from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

from django_cotton_components.infolists import (
    BadgeEntry,
    BooleanEntry,
    DateEntry,
    Infolist,
    TextEntry,
)
from django_cotton_components.panels import (
    BarListWidget,
    ChartWidget,
    DashboardPage,
    Panel,
    PanelPage,
    Resource,
    StatWidget,
    TableWidget,
)
from django_cotton_components.tables import (
    BadgeColumn,
    BooleanColumn,
    DateColumn,
    SelectFilter,
    Table,
    TernaryFilter,
    TextColumn,
)

from .models import Article, Author, Comment
from .schemas import article_schema


def _articles_over_time(request):
    rows = (
        Article.objects.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(n=Count("id"))
        .order_by("month")
    )
    return [(row["month"].strftime("%b %Y") if row["month"] else "—", row["n"]) for row in rows]


def _recent_articles_table(request):
    return (
        Table.make(Article.objects.select_related("author").order_by("-created_at")[:5])
        .id("dash-recent")
        .columns(
            [
                TextColumn.make("title").limit(50),
                TextColumn.make("author.name").label("Author"),
                BadgeColumn.make("status"),
            ]
        )
        .client_side()
        .presentation("feed")
    )


class DemoDashboard(DashboardPage):
    page_title = "Overview"
    nav_label = "Dashboard"
    nav_icon = "gauge-high"

    def widgets(self, request):
        now = timezone.now()
        since = now - timezone.timedelta(days=30)
        by_status = dict(Article.objects.values_list("status").annotate(n=Count("id")))
        return [
            StatWidget.make("Articles", Article.objects.count())
            .icon("newspaper")
            .description(f"+{Article.objects.filter(created_at__gte=since).count()} in 30 days"),
            StatWidget.make("Live", by_status.get("live", 0)).icon("tower-broadcast"),
            StatWidget.make("Featured", Article.objects.filter(featured=True).count()).icon("star"),
            StatWidget.make(
                "Comments to review",
                lambda request: Comment.objects.filter(approved=False).count(),
            )
            .icon("comments")
            .poll(30),
            ChartWidget.make("Articles over time")
            .kind("area")
            .data(_articles_over_time)
            .columns(2),
            BarListWidget.make("Articles by status").data(
                [(s.title(), by_status.get(s, 0)) for s in ("live", "draft", "archived")]
            ),
            TableWidget.make("Recent articles", _recent_articles_table),
        ]


class ReportsPage(PanelPage):
    """A custom (non-resource) panel page — demonstrates Panel.pages()."""

    template_name = "demo/panel_reports.html"
    slug = "reports"
    nav_label = "Reports"
    nav_icon = "chart-column"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["by_author"] = (
            Author.objects.annotate(n=Count("articles")).order_by("-n").values("name", "n")[:8]
        )
        return ctx


class ArticleResource(Resource):
    model = Article
    navigation_icon = "newspaper"

    @classmethod
    def build_schema(cls, *, request):
        return article_schema()

    @classmethod
    def build_infolist(cls, *, request):
        return Infolist.make().schema(
            [
                TextEntry.make("title"),
                TextEntry.make("author.name").label("Author"),
                BadgeEntry.make("status").colors({"live": "success", "archived": "muted"}),
                BooleanEntry.make("featured"),
                DateEntry.make("created_at").since(),
                TextEntry.make("body").placeholder("(no body)"),
            ]
        )

    @classmethod
    def build_table(cls, *, request):
        return (
            Table.make(cls.get_queryset(request).select_related("author"))
            .id("panel-articles")
            .columns(
                [
                    TextColumn.make("title").sortable().searchable().limit(60),
                    TextColumn.make("author.name")
                    .label("Author")
                    .sortable(sort_field="author__name"),
                    BadgeColumn.make("status").sortable(),
                    BooleanColumn.make("featured"),
                    DateColumn.make("created_at").since().sortable(),
                ]
            )
            .filters(
                [
                    SelectFilter.make("status").options(Article.Status.choices),
                    TernaryFilter.make("featured"),
                ]
            )
            .searchable()
            .default_sort("-created_at")
        )


class AuthorResource(Resource):
    model = Author
    navigation_icon = "user"

    @classmethod
    def build_table(cls, *, request):
        return (
            Table.make(cls.get_queryset(request))
            .id("panel-authors")
            .columns(
                [
                    TextColumn.make("name").sortable().searchable(),
                    TextColumn.make("email").searchable(),
                ]
            )
            .searchable()
        )


admin_panel = (
    Panel("admin")
    .path("panel")
    .brand("Demo Admin", "gauge-high")
    .pages([DemoDashboard, ReportsPage])
    .resources([ArticleResource, AuthorResource])
    .studio()  # in-browser builder at /panel/studio/ (needs dcc_studio.use_studio)
    .auth(lambda r: r.user.is_authenticated)
)
