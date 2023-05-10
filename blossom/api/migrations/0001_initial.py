# Generated by Django 2.2.12 on 2020-05-06 02:50

import django.utils.timezone
from django.db import migrations, models

import blossom.api.models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Source",
            fields=[
                (
                    "name",
                    models.CharField(max_length=20, primary_key=True, serialize=False),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Submission",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "original_id",
                    models.CharField(default=blossom.api.models.create_id, max_length=36),
                ),
                (
                    "create_time",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                (
                    "last_update_time",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("redis_id", models.CharField(blank=True, max_length=12, null=True)),
                (
                    "claim_time",
                    models.DateTimeField(blank=True, default=None, null=True),
                ),
                (
                    "complete_time",
                    models.DateTimeField(blank=True, default=None, null=True),
                ),
                ("url", models.URLField(blank=True, null=True)),
                ("tor_url", models.URLField(blank=True, null=True)),
                ("archived", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="Transcription",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "create_time",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                (
                    "last_update_time",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("original_id", models.CharField(max_length=36)),
                ("url", models.URLField(blank=True, null=True)),
                (
                    "text",
                    models.TextField(blank=True, max_length=4294000000, null=True),
                ),
                ("removed_from_reddit", models.BooleanField(default=False)),
            ],
        ),
    ]
