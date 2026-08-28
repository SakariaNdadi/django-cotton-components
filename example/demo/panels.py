from django_cotton_components.panels import Panel, Resource
from django_cotton_components.tables import BadgeColumn, BooleanColumn, DateColumn, TextColumn
from django_cotton_components.tables.table import Table

from .models import Article, Author
from .schemas import article_schema


class ArticleResource(Resource):
    model = Article
    navigation_icon = "grid"

    @classmethod
    def build_schema(cls, *, request):
        return article_schema()

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
        )


admin_panel = (
    Panel("admin")
    .path("panel")
    .resources([ArticleResource, AuthorResource])
    .auth(lambda r: r.user.is_authenticated)
)
