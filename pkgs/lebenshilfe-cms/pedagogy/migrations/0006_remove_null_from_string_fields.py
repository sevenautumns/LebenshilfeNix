from django.db import migrations, models


def forwards(apps, schema_editor):
    Supervision = apps.get_model("pedagogy", "Supervision")
    Supervision.objects.filter(class_name__isnull=True).update(class_name="")

    Request = apps.get_model("pedagogy", "Request")
    Request.objects.filter(notes__isnull=True).update(notes="")


class Migration(migrations.Migration):

    dependencies = [
        ("pedagogy", "0005_db_index_to_meta_indexes"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="supervision",
            name="class_name",
            field=models.CharField(blank=True, max_length=100, verbose_name="Klasse"),
        ),
        migrations.AlterField(
            model_name="request",
            name="notes",
            field=models.TextField(blank=True, verbose_name="Notizen"),
        ),
    ]
