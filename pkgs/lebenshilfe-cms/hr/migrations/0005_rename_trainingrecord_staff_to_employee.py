from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("hr", "0004_rename_employee_fields"),
    ]

    operations = [
        migrations.RenameField(
            model_name="trainingrecord",
            old_name="staff",
            new_name="employee",
        ),
    ]
