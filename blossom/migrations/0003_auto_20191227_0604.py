# Generated by Django 2.2.9 on 2019-12-27 06:04

import blossom.api.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('rest_framework_api_key', '0004_prefix_hashed_key'),
        ('blossom', '0002_auto_20191207_0634'),
    ]

    operations = [
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('submission_id', models.CharField(default=blossom.api.models.create_id, max_length=36)),
                ('submission_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('redis_id', models.CharField(blank=True, max_length=12, null=True)),
                ('claim_time', models.DateTimeField(blank=True, default=None, null=True)),
                ('complete_time', models.DateTimeField(blank=True, default=None, null=True)),
                ('source', models.CharField(max_length=20)),
                ('url', models.CharField(blank=True, max_length=2083, null=True)),
                ('tor_url', models.CharField(blank=True, max_length=2083, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='blossomuser',
            name='accepted_coc',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='blossomuser',
            name='api_key',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rest_framework_api_key.APIKey'),
        ),
        migrations.AddField(
            model_name='blossomuser',
            name='is_grafeas_staff',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='blossomuser',
            name='is_volunteer',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='Transcription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('post_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('transcription_id', models.CharField(max_length=36)),
                ('completion_method', models.CharField(max_length=20)),
                ('url', models.CharField(blank=True, max_length=2083, null=True)),
                ('text', models.TextField(max_length=4294000000)),
                ('ocr_text', models.TextField(blank=True, max_length=4294000000, null=True)),
                ('removed_from_reddit', models.BooleanField(default=False)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='blossom.Submission')),
            ],
        ),
        migrations.AddField(
            model_name='submission',
            name='claimed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='claimed_by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='submission',
            name='completed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='completed_by', to=settings.AUTH_USER_MODEL),
        ),
    ]