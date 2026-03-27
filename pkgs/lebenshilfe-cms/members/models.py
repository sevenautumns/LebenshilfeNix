from django.db import models
from django.db.models import Q, F, CheckConstraint
from base.models import Person
from base.fields import EuroDecimalField


class Member(Person):
    entrance_date = models.DateField(verbose_name="Eintrittsdatum")
    leaving_date = models.DateField(
        blank=True, null=True, verbose_name="Austrittsdatum"
    )
    membership_fee = EuroDecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Beitragshöhe",
        help_text="Monatlicher Mitgliedsbeitrag in Euro",
    )
    authorization_id = models.CharField(
        max_length=100,
        verbose_name="Mandatsreferenz-Nr.",
        help_text="Referenznummer des SEPA-Lastschriftmandats",
    )

    class Meta:
        verbose_name = "Mitglied"
        verbose_name_plural = "Mitglieder"
        ordering = ["last_name", "first_name"]
        constraints = [
            CheckConstraint(
                condition=Q(leaving_date__isnull=True)
                | Q(leaving_date__gte=F("entrance_date")),
                name="member_leaving_date_after_entrance_date",
            )
        ]

    def __str__(self):
        return super().__str__()
