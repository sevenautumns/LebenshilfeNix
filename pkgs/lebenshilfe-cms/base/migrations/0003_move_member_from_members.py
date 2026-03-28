import base.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0002_move_denomination_to_hr"),
        ("members", "0002_move_member_to_base"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Member",
                    fields=[
                        (
                            "person_ptr",
                            models.OneToOneField(
                                auto_created=True,
                                on_delete=django.db.models.deletion.CASCADE,
                                parent_link=True,
                                primary_key=True,
                                serialize=False,
                                to="base.person",
                            ),
                        ),
                        (
                            "entrance_date",
                            models.DateField(verbose_name="Eintrittsdatum"),
                        ),
                        (
                            "leaving_date",
                            models.DateField(
                                blank=True, null=True, verbose_name="Austrittsdatum"
                            ),
                        ),
                        (
                            "membership_fee",
                            base.fields.EuroDecimalField(
                                decimal_places=2,
                                help_text="Monatlicher Mitgliedsbeitrag in Euro",
                                max_digits=10,
                                verbose_name="Beitragshöhe",
                            ),
                        ),
                        (
                            "authorization_id",
                            models.CharField(
                                help_text="Referenznummer des SEPA-Lastschriftmandats",
                                max_length=100,
                                verbose_name="Mandatsreferenz-Nr.",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Mitglied",
                        "verbose_name_plural": "Mitglieder",
                        "ordering": ["last_name", "first_name"],
                        "db_table": "members_member",
                        "constraints": [
                            models.CheckConstraint(
                                condition=models.Q(
                                    ("leaving_date__isnull", True),
                                    ("leaving_date__gte", models.F("entrance_date")),
                                    _connector="OR",
                                ),
                                name="member_leaving_date_after_entrance_date",
                            )
                        ],
                    },
                    bases=("base.person",),
                ),
            ],
            database_operations=[],
        ),
    ]
