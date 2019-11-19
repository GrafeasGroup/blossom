from django.db import models
from django.contrib.auth.models import User

class Post(models.Model):
    title = models.CharField(max_length=70)
    body = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    # about page, for example
    standalone_section = models.BooleanField()
    published = models.BooleanField()
    header_order = models.IntegerField(
        help_text="Optional: an integer from 1-99 -- lower numbers will appear more to the left.",
        blank=True, null=True
    )
