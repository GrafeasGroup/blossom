# Generated by Django 3.2.10 on 2022-01-06 20:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0005_blossomuser_is_bot"),
    ]

    operations = [
        migrations.AddField(
            model_name="blossomuser",
            name="overwrite_check_percentage",
            field=models.FloatField(blank=True, default=None, null=True),
        ),
    ]