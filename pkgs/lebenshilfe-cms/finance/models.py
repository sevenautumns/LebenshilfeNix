from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from base.models import CostPayerLink


class CostPayer(models.Model):
    identifier = models.CharField(max_length=255, unique=True, verbose_name="Name")

    class Meta:
        verbose_name = "Kostenzahler"
        verbose_name_plural = "Kostenzahler"

    def __str__(self):
        return self.identifier


class FeeAgreement(models.Model):
    label = models.CharField(max_length=255, verbose_name="Bezeichnung")
    valid_from = models.DateField(verbose_name="Gültig von")
    valid_to = models.DateField(verbose_name="Gültig bis")
    price_standard = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Schulbegleitung (allgemein)"
    )
    price_tandem = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Tandem"
    )
    price_coordination = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Koordination"
    )
    payers = GenericRelation(CostPayerLink)

    class Meta:
        verbose_name = "Entgeltvereinbarung"
        verbose_name_plural = "Entgeltvereinbarungen"

    def __str__(self):
        return f"{self.label} ({self.valid_from} - {self.valid_to})"


class PoolAgreement(models.Model):
    valid_from = models.DateField(verbose_name="Gültig von")
    valid_to = models.DateField(verbose_name="Gültig bis")
    installment = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Abschlag"
    )
    payer = models.ForeignKey(
        CostPayer, on_delete=models.PROTECT, verbose_name="Kostenzahler"
    )

    class Meta:
        verbose_name = "Poolvereinbarung"
        verbose_name_plural = "Poolvereinbarungen"

    def __str__(self):
        return f"Poolvereinbarung {self.payer} ({self.valid_from})"


class Payment(models.Model):
    supervision = models.ForeignKey(
        "pedagogy.Supervision", on_delete=models.PROTECT, verbose_name="Betreuung"
    )
    payer = models.ForeignKey(
        CostPayer, on_delete=models.PROTECT, verbose_name="Kostenzahler"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Betrag")
    payment_date = models.DateField(verbose_name="Zahlungsdatum")
    note = models.TextField(blank=True, null=True, verbose_name="Notiz")

    class Meta:
        verbose_name = "Zahlung"
        verbose_name_plural = "Zahlungen"

    def __str__(self):
        return f"Zahlung: {self.amount}€ von {self.payer}"
