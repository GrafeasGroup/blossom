# Generated by Django 3.2.12 on 2022-02-25 20:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0020_transcriptioncheck"),
    ]

    operations = [
        migrations.AddField(
            model_name="transcriptioncheck",
            name="slack_channel_id",
            field=models.CharField(blank=True, default=None, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="transcriptioncheck",
            name="slack_message_ts",
            field=models.CharField(blank=True, default=None, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="transcriptioncheck",
            name="trigger",
            field=models.CharField(max_length=200, null=True),
        ),
    ]
