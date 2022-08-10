from django.contrib.auth import get_user_model
from django.db import models
from django.shortcuts import reverse
from django.utils import timezone
from django.utils.text import slugify


class Post(models.Model):
    title = models.CharField(max_length=300)
    body = models.TextField()
    author = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)

    # something that will go on grafeas.org/engineering/
    engineeringblogpost = models.BooleanField(
        default=False, help_text="Mark this post as an engineering blog post."
    )

    # about page, for example
    standalone_section = models.BooleanField(default=False)

    slug = models.SlugField(default="", editable=False, max_length=300)
    published = models.BooleanField(default=False)
    header_order = models.IntegerField(
        help_text="Optional: an integer from 1-99 -- lower numbers will appear "
        "more to the left.",
        blank=True,
        null=True,
    )
    show_in_news_view = models.BooleanField(default=True)

    def get_absolute_url(self) -> str:
        """Return the full url of a given post."""
        kwargs = {"slug": self.slug}
        return reverse("post_detail", kwargs=kwargs)

    def save(self, *args: object, **kwargs: object) -> None:
        """Override the save functionality to set the slug for a post."""
        value = self.title
        self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.standalone_section:
            return f"Section | Header order {self.header_order}: {self.title}"
        return self.title
