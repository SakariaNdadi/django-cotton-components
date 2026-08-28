from __future__ import annotations

from django.contrib.auth import views as auth_views
from django.db.models import Count
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, TemplateView, UpdateView

from django_cotton_components.mixins import SchemaFormMixin
from django_cotton_components.schemas import Schema, TextInput
from django_cotton_components.tables.views import TableMixin
from django_cotton_components.wizards import WizardStep, WizardView

from .forms import ArticleForm
from .models import Article, Author, Comment
from .schemas import article_schema
from .tables import article_table, needs_review_table, recent_articles_table


class DashboardView(TemplateView):
    template_name = "demo/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        since = timezone.now() - timezone.timedelta(days=30)
        by_status = dict(Article.objects.values_list("status").annotate(n=Count("id")))
        ctx["stats"] = {
            "total": Article.objects.count(),
            "live": by_status.get("live", 0),
            "drafts": by_status.get("draft", 0),
            "new_30d": Article.objects.filter(created_at__gte=since).count(),
            "pending_comments": Comment.objects.filter(approved=False).count(),
        }
        ctx["recent_table"] = recent_articles_table(self.request).render(self.request)
        ctx["needs_review_table"] = needs_review_table(self.request).render(self.request)
        ctx["featured"] = Article.objects.filter(featured=True).count()
        return ctx


class ArticleListView(TableMixin, TemplateView):
    template_name = "demo/article_list.html"

    def get_table(self):
        return article_table(self.request)


class ArticleCreateView(SchemaFormMixin, CreateView):
    model = Article
    template_name = "demo/article_form.html"
    success_url = reverse_lazy("demo:article-list")

    def get_schema(self):
        return article_schema()


class ArticleUpdateView(SchemaFormMixin, UpdateView):
    model = Article
    template_name = "demo/article_form.html"
    success_url = reverse_lazy("demo:article-list")

    def get_schema(self):
        return article_schema()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["is_edit"] = True
        return ctx


class ArticleWizard(WizardView):
    steps_config = [
        WizardStep(
            "content",
            Schema.make()
            .form(ArticleForm)
            .strict()
            .schema([TextInput.make("title"), TextInput.make("slug")]),
            title="Content",
        ),
        WizardStep(
            "publish",
            Schema.make().form(ArticleForm).strict().schema([TextInput.make("status")]),
            title="Publish",
        ),
    ]
    template_name = "demo/wizard.html"

    def done(self, form_list, **kwargs):
        data = {}
        for form in form_list:
            data.update(form.cleaned_data)
        Article.objects.create(author=Author.objects.first(), **data)
        return redirect("demo:article-list")


class ComponentsView(TemplateView):
    template_name = "demo/components.html"

    def get_context_data(self, **kwargs):
        from django_cotton_components.schemas import (
            MultiSelect,
            Schema,
            Section,
            Select,
            Textarea,
            Toggle,
        )

        ctx = super().get_context_data(**kwargs)
        fields = ["title", "slug", "body", "status", "author", "tags", "featured"]
        schema = (
            Schema.make()
            .model(Article, fields=fields)
            .schema(
                [
                    Section.make("Text").schema(
                        [
                            TextInput.make("title").help_text("A plain text input."),
                            TextInput.make("slug").help_text("Lowercase, dashes."),
                            Textarea.make("body"),
                        ]
                    ),
                    Section.make("Choice").schema(
                        [
                            Select.make("status").searchable(),
                            Select.make("author").searchable().help_text("Type to filter."),
                            MultiSelect.make("tags").help_text("Multi-select combobox."),
                        ]
                    ),
                    Section.make("Boolean").schema([Toggle.make("featured")]),
                ]
            )
        )
        ctx["controls_html"] = schema.render(request=self.request, form=schema.build_form())
        return ctx


class DemoLogin(auth_views.LoginView):
    template_name = "demo/login.html"
    redirect_authenticated_user = True


class DemoLogout(auth_views.LogoutView):
    next_page = reverse_lazy("demo:index")
