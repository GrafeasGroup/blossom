# Generated by Django 2.2.12 on 2020-08-29 21:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0006_auto_20200829_2100"),
    ]

    operations = [
        migrations.AddField(
            model_name="source", name="id", field=models.IntegerField(default=0),
        ),
    ]