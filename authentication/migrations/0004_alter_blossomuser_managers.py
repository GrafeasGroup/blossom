# Generated by Django 3.2.3 on 2021-08-31 14:24

from django.db import migrations

import authentication.models


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0003_auto_20210608_1743"),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="blossomuser",
            managers=[("objects", authentication.models.BlossomUserManager())],
        ),
    ]