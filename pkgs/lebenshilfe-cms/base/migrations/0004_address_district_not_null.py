from django.db import migrations, models


def forwards(apps, schema_editor):
    apps.get_model("base", "Address").objects.filter(district__isnull=True).update(
        district=""
    )


class Migration(migrations.Migration):

    dependencies = [
        ("base", "0003_rename_telephone_number_to_number"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="address",
            name="district",
            field=models.CharField(blank=True, max_length=255, verbose_name="Ortsteil"),
        ),
    ]
