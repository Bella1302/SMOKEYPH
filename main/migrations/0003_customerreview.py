from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0002_admin_activity"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomerReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("comment", models.TextField(max_length=1000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Customer Review",
                "verbose_name_plural": "Customer Reviews",
                "ordering": ["-created_at"],
            },
        ),
    ]
