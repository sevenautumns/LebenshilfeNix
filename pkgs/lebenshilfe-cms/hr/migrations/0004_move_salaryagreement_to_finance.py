from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("hr", "0003_move_denomination_from_base"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel("SalaryAgreement"),
            ],
            database_operations=[],
        ),
    ]
