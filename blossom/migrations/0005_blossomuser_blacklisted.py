# Generated by Django 2.2.9 on 2020-02-08 22:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blossom', '0004_auto_20200109_0004'),
    ]

    operations = [
        migrations.AddField(
            model_name='blossomuser',
            name='blacklisted',
            field=models.BooleanField(default=False),
        ),
    ]
