import base.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0002_initial"),
        ("hr", "0004_move_salaryagreement_to_finance"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="SalaryAgreement",
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
                            "salary_standard",
                            base.fields.EuroDecimalField(
                                decimal_places=2,
                                max_digits=10,
                                verbose_name="Schulbegleitung (allgemein)",
                            ),
                        ),
                        (
                            "salary_tandem",
                            base.fields.EuroDecimalField(
                                decimal_places=2,
                                max_digits=10,
                                verbose_name="Tandem",
                            ),
                        ),
                        (
                            "salary_coordination",
                            base.fields.EuroDecimalField(
                                decimal_places=2,
                                max_digits=10,
                                verbose_name="Koordination",
                            ),
                        ),
                        (
                            "salary_management",
                            base.fields.EuroDecimalField(
                                decimal_places=2,
                                max_digits=10,
                                verbose_name="Geschäftsführung",
                            ),
                        ),
                        (
                            "valid_from",
                            models.DateField(verbose_name="Gültig von"),
                        ),
                        (
                            "valid_to",
                            models.DateField(verbose_name="Gültig bis"),
                        ),
                    ],
                    options={
                        "verbose_name": "Gehaltsvereinbarung",
                        "verbose_name_plural": "Gehaltsvereinbarungen",
                        "ordering": ["-valid_from"],
                        "db_table": "hr_salaryagreement",
                        "constraints": [
                            models.CheckConstraint(
                                condition=models.Q(
                                    ("valid_to__gte", models.F("valid_from"))
                                ),
                                name="salaryagreement_valid_to_after_valid_from",
                            )
                        ],
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
