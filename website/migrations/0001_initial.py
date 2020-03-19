# Generated by Django 2.2.11 on 2020-03-19 21:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=70)),
                ('body', models.TextField()),
                ('date', models.DateTimeField(default=django.utils.timezone.now)),
                ('engineeringblogpost', models.BooleanField(default=False, help_text='Mark this post as an engineering blog post.')),
                ('standalone_section', models.BooleanField(default=False)),
                ('slug', models.SlugField(default='', editable=False, max_length=70)),
                ('published', models.BooleanField(default=False)),
                ('header_order', models.IntegerField(blank=True, help_text='Optional: an integer from 1-99 -- lower numbers will appear more to the left.', null=True)),
                ('show_in_news_view', models.BooleanField(default=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
