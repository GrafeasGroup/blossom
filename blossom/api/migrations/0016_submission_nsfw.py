# Generated by Django 3.2.9 on 2021-12-08 22:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0015_submission_title"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="nsfw",
            field=models.BooleanField(blank=True, null=True),
        ),
    ]