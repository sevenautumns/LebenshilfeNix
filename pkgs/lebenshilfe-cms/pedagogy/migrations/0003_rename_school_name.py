from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("pedagogy", "0002_rename_date_fields"),
    ]

    operations = [
        migrations.RenameField(
            model_name="school",
            old_name="school_name",
            new_name="name",
        ),
    ]
