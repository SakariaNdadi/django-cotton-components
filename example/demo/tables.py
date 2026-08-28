from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from django_cotton_components.actions import Action, BulkAction
from django_cotton_components.tables import (
    BooleanColumn,
    DateColumn,
    SelectFilter,
    Table,
    TernaryFilter,
    TextColumn,
)

from .models import Article

_STATUS_CLASS = {"live": "is-live", "draft": "is-draft", "archived": "is-archived"}


def _author_cell(record):
    author = record.author
    avatar = (
        format_html('<img class="demo-avatar" src="{}" alt="">', author.avatar.url)
        if author.avatar
        else mark_safe('<span class="demo-avatar"></span>')
    )
    return format_html('<span class="demo-authorcell">{}{}</span>', avatar, author.name)


def _status_cell(record):
    cls = _STATUS_CLASS.get(record.status, "")
    return format_html('<span class="dcc-badge {}">{}</span>', cls, record.get_status_display())


def article_table(request):
    return (
        Table.make(Article.objects.select_related("author"))
        .id("articles")
        .columns(
            [
                TextColumn.make("title").sortable().searchable().limit(64),
                TextColumn.make("author.name")
                .label("Author")
                .sortable(sort_field="author__name")
                .searchable(["author__name"])
                .state(_author_cell)
                .allow_html(),
                TextColumn.make("status")
                .label("Status")
                .sortable()
                .state(_status_cell)
                .allow_html(),
                BooleanColumn.make("featured").labels(("★", "—")),
                DateColumn.make("created_at").label("Created").since().sortable(),
            ]
        )
        .filters(
            [
                SelectFilter.make("status").options(Article.Status.choices),
                TernaryFilter.make("featured"),
            ]
        )
        .actions(
            [
                Action.make("edit")
                .label("Edit")
                .icon("pen")
                .variant("secondary")
                .to_url(lambda record: reverse("demo:article-edit", args=[record.pk])),
                Action.make("quick_edit")
                .label("Quick edit")
                .icon("pen-to-square")
                .variant("secondary")
                .modal(_quick_edit_schema())
                .action(_save_quick_edit)
                .success_notification("Article updated"),
                Action.make("feature")
                .label("Toggle ★")
                .icon("star")
                .variant("secondary")
                .action(_toggle_featured)
                .success_notification("Updated featured flag"),
            ]
        )
        .bulk_actions(
            [
                BulkAction.make("publish")
                .label("Mark live")
                .icon("rocket")
                .requires_confirmation()
                .modal_heading("Publish the selected articles?")
                .action(lambda records: _bulk_status(records, "live"))
                .success_notification("Articles published"),
                BulkAction.make("archive")
                .label("Archive")
                .icon("box-archive")
                .requires_confirmation()
                .modal_heading("Archive the selected articles?")
                .action(lambda records: _bulk_status(records, "archived"))
                .success_notification("Articles archived"),
            ]
        )
        .default_sort("-created_at")
        .paginate([10, 25, 50])
        .empty_message("No articles match these filters.")
    )


def _quick_edit_schema():
    from django_cotton_components.schemas import Schema, Select, TextInput

    from .forms import ArticleForm

    return (
        Schema.make()
        .form(ArticleForm)
        .strict()
        .schema([TextInput.make("title").required(), Select.make("status")])
    )


def _save_quick_edit(record, data):
    record.title = data["title"]
    record.status = data["status"]
    record.save(update_fields=["title", "status"])


def _toggle_featured(record):
    record.featured = not record.featured
    record.save(update_fields=["featured"])


def _bulk_status(records, status):
    from django.db.models import QuerySet

    qs = (
        records
        if isinstance(records, QuerySet)
        else Article.objects.filter(pk__in=[r.pk for r in records])
    )
    qs.update(status=status)
