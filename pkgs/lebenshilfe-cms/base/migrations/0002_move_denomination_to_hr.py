from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel("Denomination"),
            ],
            database_operations=[],
        ),
    ]
