"""``manage.py dcc_scaffold`` — write ``DashboardSpec`` rows from live models.

manage.py dcc_scaffold blog.Article           # one model
manage.py dcc_scaffold blog.Article --dry-run  # print the spec, write nothing
manage.py dcc_scaffold --all                   # every picker-eligible model
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from ...introspect import installed_models, is_sensitive_model, resolve_model
from ...models import DashboardSpec
from ...scaffold import scaffold_spec


class Command(BaseCommand):
    help = "Create DashboardSpec rows by introspecting models."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("models", nargs="*", help="app_label.Model labels")
        parser.add_argument("--all", action="store_true", help="every eligible model")
        parser.add_argument("--dry-run", action="store_true", help="print, do not write")

    def handle(self, *args: Any, **options: Any) -> None:
        labels: list[str] = list(options["models"])
        if options["all"]:
            labels += [row["label"] for row in installed_models(None)]
        if not labels:
            raise CommandError("pass one or more app_label.Model, or --all")

        for label in dict.fromkeys(labels):
            try:
                model = resolve_model(label)
            except LookupError as exc:
                raise CommandError(f"{label}: {exc}") from None
            if is_sensitive_model(model):
                self.stderr.write(f"skip {label} (sensitive)")
                continue

            spec = scaffold_spec(model)
            if options["dry_run"]:
                self.stdout.write(f"# {label}")
                self.stdout.write(json.dumps(spec, indent=2))
                continue

            slug = model._meta.model_name or label.replace(".", "-")
            obj, created = DashboardSpec.objects.update_or_create(
                slug=slug,
                defaults={
                    "label": str(model._meta.verbose_name_plural).title(),
                    "model": label,
                    "table": spec["table"],
                    "schema": spec["schema"],
                    "infolist": spec["infolist"],
                },
            )
            verb = "created" if created else "updated"
            self.stdout.write(self.style.SUCCESS(f"{verb} {obj.slug} ({label})"))
