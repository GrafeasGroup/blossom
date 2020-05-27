# Generated by Django 2.2.12 on 2020-05-06 02:50

import api.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("api", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="transcription",
            name="author",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name="transcription",
            name="source",
            field=models.ForeignKey(
                default=api.models.get_default_source,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="api_transcription_related",
                to="api.Source",
            ),
        ),
        migrations.AddField(
            model_name="transcription",
            name="submission",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="api.Submission"
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="claimed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="claimed_by",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="completed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="completed_by",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="source",
            field=models.ForeignKey(
                default=api.models.get_default_source,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="api_submission_related",
                to="api.Source",
            ),
        ),
    ]
