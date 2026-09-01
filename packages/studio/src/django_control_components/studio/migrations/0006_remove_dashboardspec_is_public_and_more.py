"""Replace the ``is_public`` boolean with the three-state ``visibility`` field.

Lossless: ``is_public=True`` carried the documented meaning "visible to every
authenticated user" -> ``AUTHENTICATED``; ``is_public=False`` -> ``RESTRICTED``.
No row becomes ``PUBLIC`` automatically -- that is a new capability an author
opts into.
"""

from typing import Any

from django.db import migrations, models

_CHOICES = [
    ("public", "Everyone, including signed-out visitors"),
    ("auth", "Any signed-in user"),
    ("restricted", "Only the groups / users / permission below"),
]
_MODELS = ("dashboardspec", "navitem", "paneldashboard")


def _forward(apps: Any, schema_editor: Any) -> None:
    for name in _MODELS:
        model = apps.get_model("dcc_studio", name)
        model.objects.filter(is_public=True).update(visibility="auth")
        model.objects.filter(is_public=False).update(visibility="restricted")


def _backward(apps: Any, schema_editor: Any) -> None:
    for name in _MODELS:
        model = apps.get_model("dcc_studio", name)
        model.objects.filter(visibility="restricted").update(is_public=False)
        model.objects.exclude(visibility="restricted").update(is_public=True)


class Migration(migrations.Migration):
    dependencies = [
        ("dcc_studio", "0005_studioentry"),
    ]

    operations = [
        # add the new field first so the data step can populate it...
        migrations.AddField(
            model_name="dashboardspec",
            name="visibility",
            field=models.CharField(choices=_CHOICES, default="restricted", max_length=10),
        ),
        migrations.AddField(
            model_name="navitem",
            name="visibility",
            field=models.CharField(choices=_CHOICES, default="restricted", max_length=10),
        ),
        migrations.AddField(
            model_name="paneldashboard",
            name="visibility",
            field=models.CharField(choices=_CHOICES, default="restricted", max_length=10),
        ),
        migrations.RunPython(_forward, _backward),
        # ...then drop the old one.
        migrations.RemoveField(model_name="dashboardspec", name="is_public"),
        migrations.RemoveField(model_name="navitem", name="is_public"),
        migrations.RemoveField(model_name="paneldashboard", name="is_public"),
    ]
