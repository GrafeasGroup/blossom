# Generated by Django 2.2.12 on 2020-08-21 21:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_auto_20200506_1721"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="is_image",
            field=models.BooleanField(default=None, null=True),
        ),
    ]
