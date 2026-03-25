from django.db import models
from base.models import Person


class Member(Person):
    entrance_date = models.DateField(verbose_name="Eintrittsdatum")
    leaving_date = models.DateField(
        blank=True, null=True, verbose_name="Austrittsdatum"
    )
    membership_fee = models.DecimalField(
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

    def __str__(self):
        return super().__str__()
