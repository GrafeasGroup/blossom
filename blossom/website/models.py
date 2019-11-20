from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone


class Post(models.Model):
    title = models.CharField(max_length=70)
    body = models.TextField()
    author = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)

    # about page, for example
    standalone_section = models.BooleanField()
    slug = models.SlugField(
        default='',
        editable=False,
        max_length=70
    )
    published = models.BooleanField()
    header_order = models.IntegerField(
        help_text="Optional: an integer from 1-99 -- lower numbers will appear "
                  "more to the left.",
        blank=True, null=True
    )

    def get_absolute_url(self):
        kwargs = {
            'pk': self.id,
            'slug': self.slug
        }
        return reverse('post_detail', kwargs=kwargs)

    def save(self, *args, **kwargs):
        value = self.title
        self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.standalone_section:
            return f"Section | Header order {self.header_order}: {self.title}"
        return self.title
