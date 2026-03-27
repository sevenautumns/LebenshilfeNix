from django.db import models
from django.db.models import Q, F, CheckConstraint
from base.fields import EuroDecimalField


class CostPayer(models.Model):
    identifier = models.CharField(max_length=255, unique=True, verbose_name="Name")

    class Meta:
        verbose_name = "Kostenträger"
        verbose_name_plural = "Kostenträger"
        ordering = ["identifier"]

    def __str__(self):
        return self.identifier


class FeeAgreement(models.Model):
    valid_from = models.DateField(verbose_name="Gültig von")
    valid_to = models.DateField(verbose_name="Gültig bis")
    price_standard = EuroDecimalField(
        max_digits=10, decimal_places=2, verbose_name="Schulbegleitung (allgemein)"
    )
    price_tandem = EuroDecimalField(
        max_digits=10, decimal_places=2, verbose_name="Tandem"
    )
    price_coordination = EuroDecimalField(
        max_digits=10, decimal_places=2, verbose_name="Koordination"
    )
    responsible_payer = models.ForeignKey(
        CostPayer,
        on_delete=models.PROTECT,
        verbose_name="Zuständiger Kostenträger",
        related_name="responsible_fee_agreements",
    )
    additional_payers = models.ManyToManyField(
        CostPayer,
        blank=True,
        verbose_name="Weitere Kostenträger",
        related_name="additional_fee_agreements",
    )

    class Meta:
        verbose_name = "Entgeltvereinbarung"
        verbose_name_plural = "Entgeltvereinbarungen"
        ordering = ["-valid_from"]
        constraints = [
            CheckConstraint(
                condition=Q(valid_to__gte=F("valid_from")),
                name="feeagreement_valid_to_after_valid_from",
            )
        ]

    def __str__(self):
        return f"{self.responsible_payer} ({self.valid_from} – {self.valid_to})"


class PoolAgreement(models.Model):
    payer = models.ForeignKey(
        CostPayer,
        on_delete=models.PROTECT,
        related_name="pool_agreements",
        verbose_name="Kostenträger",
    )
    flat_rate = EuroDecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Pauschalentgelt pro Fall",
        help_text="Pauschalentgelt in Euro pro betreutem Fall",
    )
    max_supervisions = models.PositiveIntegerField(
        verbose_name="Max. Betreuungen",
        help_text="Anzahl der aktuell erlaubten Betreuungen laut Vereinbarung",
    )
    valid_from = models.DateField(verbose_name="Gültig von")
    valid_to = models.DateField(verbose_name="Gültig bis")

    class Meta:
        verbose_name = "Poolvereinbarung"
        verbose_name_plural = "Poolvereinbarungen"
        ordering = ["-valid_from"]
        constraints = [
            CheckConstraint(
                condition=Q(valid_to__gte=F("valid_from")),
                name="poolagreement_valid_to_after_valid_from",
            )
        ]

    def __str__(self):
        return f"Poolvereinbarung {self.payer} ({self.valid_from})"


class Payment(models.Model):
    supervision = models.ForeignKey(
        "pedagogy.Supervision",
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="Betreuung",
    )
    payer = models.ForeignKey(
        CostPayer,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name="Kostenträger",
    )
    amount = EuroDecimalField(max_digits=10, decimal_places=2, verbose_name="Betrag")
    payment_date = models.DateField(verbose_name="Zahlungsdatum")
    note = models.TextField(blank=True, null=True, verbose_name="Notiz")

    class Meta:
        verbose_name = "Zahlung"
        verbose_name_plural = "Zahlungen"
        ordering = ["-payment_date"]

    def __str__(self):
        return f"Zahlung: {self.amount}€ von {self.payer}"
