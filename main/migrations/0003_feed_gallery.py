# Generated migration for feed/gallery models with sample seed data

from django.db import migrations, models
from django.utils import timezone
from datetime import timedelta


def seed_feed_data(apps, schema_editor):
    FeedPost = apps.get_model("main", "FeedPost")
    if FeedPost.objects.exists():
        return
    now = timezone.now()
    FeedPost.objects.create(
        author_name="Tony S.",
        author_initial="T",
        content="The professional staff was extremely charming and the food was spectacular.",
        is_team_update=False,
        likes=4,
        created_at=now - timedelta(days=12),
    )
    FeedPost.objects.create(
        author_name="Smokey Peeks",
        author_initial="",
        content="A new experience is about to begin.",
        is_team_update=True,
        likes=0,
        created_at=now - timedelta(days=13),
    )


def unseed_feed_data(apps, schema_editor):
    FeedPost = apps.get_model("main", "FeedPost")
    FeedPost.objects.filter(
        author_name__in=["Tony S.", "Smokey Peeks"],
        content__in=[
            "The professional staff was extremely charming and the food was spectacular.",
            "A new experience is about to begin.",
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0002_admin_activity"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeedPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("author_name", models.CharField(max_length=120)),
                ("author_initial", models.CharField(blank=True, max_length=1)),
                ("content", models.TextField()),
                ("is_team_update", models.BooleanField(default=False)),
                ("likes", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Feed Post",
                "verbose_name_plural": "Feed Posts",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Album",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("cover_url", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Album",
                "verbose_name_plural": "Albums",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AlbumPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cloud_url", models.CharField(max_length=500)),
                ("caption", models.CharField(blank=True, max_length=200)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("album", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="photos", to="main.album")),
            ],
            options={
                "verbose_name": "Album Photo",
                "verbose_name_plural": "Album Photos",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.RunPython(seed_feed_data, unseed_feed_data),
    ]
