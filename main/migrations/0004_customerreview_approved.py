from django.db import migrations, models


def approve_existing_reviews(apps, schema_editor):
    CustomerReview = apps.get_model("main", "CustomerReview")
    CustomerReview.objects.all().update(approved=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0003_customerreview"),
    ]

    operations = [
        migrations.AddField(
            model_name="customerreview",
            name="approved",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(approve_existing_reviews, noop_reverse),
    ]
