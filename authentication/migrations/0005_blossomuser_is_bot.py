# Generated by Django 3.2.10 on 2021-12-28 21:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0004_alter_blossomuser_managers"),
    ]

    operations = [
        migrations.AddField(
            model_name="blossomuser",
            name="is_bot",
            field=models.BooleanField(default=False),
        ),
    ]
