import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0002_move_denomination_to_hr"),
        ("hr", "0002_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Denomination",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "name",
                            models.CharField(
                                max_length=100, unique=True, verbose_name="Name"
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Konfession",
                        "verbose_name_plural": "Konfessionen",
                        "ordering": ["name"],
                        "db_table": "base_denomination",
                    },
                ),
                migrations.AlterField(
                    model_name="employee",
                    name="church_membership",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="employees",
                        to="hr.denomination",
                        verbose_name="Kirchenmitgliedschaft",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
