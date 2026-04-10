from django.db import migrations


class Migration(migrations.Migration):
    """
    Entfernt tandem und is_tandem_prophylactic von Supervision,
    nachdem die Datenmigration (0018) alle Tandem-Daten in TandemPairing überführt hat.
    """

    dependencies = [
        ("pedagogy", "0018_migrate_tandem_to_tandempairing"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="supervision",
            name="is_tandem_prophylactic",
        ),
        migrations.RemoveField(
            model_name="supervision",
            name="tandem",
        ),
    ]
