# Generated migration for Album models with local image storage

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0005_feedpost_feedlike_sitevisitcounter"),
    ]

    operations = [
        migrations.CreateModel(
            name="Album",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("author_name", models.CharField(blank=True, max_length=120)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("approved", models.BooleanField(default=False)),
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
                ("image", models.ImageField(upload_to="albums/%Y/%m/")),
                ("caption", models.CharField(blank=True, max_length=200)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                (
                    "album",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="photos",
                        to="main.album",
                    ),
                ),
            ],
            options={
                "verbose_name": "Album Photo",
                "verbose_name_plural": "Album Photos",
                "ordering": ["sort_order", "id"],
            },
        ),
    ]
