# Generated manually for Feed feature

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("main", "0004_customerreview_approved"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteVisitCounter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("total_visits", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Site Visit Counter",
                "verbose_name_plural": "Site Visit Counter",
            },
        ),
        migrations.CreateModel(
            name="FeedPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "post_type",
                    models.CharField(
                        choices=[("customer", "Customer Experience"), ("update", "Management Update")],
                        default="customer",
                        max_length=20,
                    ),
                ),
                ("author_name", models.CharField(blank=True, max_length=120)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("caption", models.TextField(blank=True, max_length=1000)),
                ("image", models.ImageField(blank=True, null=True, upload_to="feed/%Y/%m/")),
                ("approved", models.BooleanField(default=False)),
                ("pinned", models.BooleanField(default=False)),
                ("like_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="feed_posts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Feed Post",
                "verbose_name_plural": "Feed Posts",
                "ordering": ["-pinned", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="FeedLike",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_key", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "post",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="likes", to="main.feedpost"),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("post", "session_key"), name="unique_feed_like_per_session"),
                ],
            },
        ),
    ]
