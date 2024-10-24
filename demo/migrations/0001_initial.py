# Generated by Django 5.1.2 on 2024-10-23 08:13

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Car",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("manufacturer", models.CharField(max_length=50)),
                ("model", models.CharField(max_length=50)),
                ("year", models.IntegerField()),
                (
                    "transmission",
                    models.CharField(
                        choices=[("Automatic", "Automatic"), ("Manual", "Manual")],
                        max_length=10,
                    ),
                ),
                ("color", models.CharField(max_length=20)),
            ],
        ),
    ]
