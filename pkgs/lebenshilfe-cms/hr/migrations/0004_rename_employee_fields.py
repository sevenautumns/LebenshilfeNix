from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0003_rename_absence_date_fields"),
    ]

    operations = [
        migrations.RenameField(
            model_name="employee",
            old_name="lh_start",
            new_name="lebenshilfe_start_date",
        ),
        migrations.RenameField(
            model_name="employee",
            old_name="criminal_record_certificate",
            new_name="criminal_record_certificate_date",
        ),
    ]
