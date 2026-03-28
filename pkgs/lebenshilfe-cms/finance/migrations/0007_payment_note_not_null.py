from django.db import migrations, models


def forwards(apps, schema_editor):
    apps.get_model("finance", "Payment").objects.filter(note__isnull=True).update(
        note=""
    )


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0006_db_index_to_meta_indexes"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="payment",
            name="note",
            field=models.TextField(blank=True, verbose_name="Notiz"),
        ),
    ]
