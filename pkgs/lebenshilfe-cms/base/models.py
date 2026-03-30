from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db.models import Case, When, Value, F, Q, CheckConstraint
from django.db.models.functions import Concat
from phonenumber_field.modelfields import PhoneNumberField
from .fields import EuroDecimalField


class Address(models.Model):
    primary = models.BooleanField(default=False, verbose_name="Primär")
    street = models.CharField(max_length=255, verbose_name="Straße")
    house_number = models.CharField(max_length=50, verbose_name="Hausnummer")
    postcode = models.CharField(max_length=10, verbose_name="Postleitzahl")
    city = models.CharField(max_length=255, verbose_name="Stadt")
    district = models.CharField(
        max_length=255, blank=True, verbose_name="Ortsteil"
    )

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="+"
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = "Adresse"
        verbose_name_plural = "Adressen"
        ordering = ["-primary", "street"]

    def __str__(self):
        ort = f"{self.postcode} {self.city}"
        if self.district:
            ort += f" ({self.district})"
        return f"{self.street} {self.house_number}, {ort}"


class Phone(models.Model):
    number = PhoneNumberField(region="DE", verbose_name="Telefonnummer")
    primary = models.BooleanField(default=False, verbose_name="Primär")

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="+"
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = "Telefonnummer"
        verbose_name_plural = "Telefonnummern"
        ordering = ["-primary"]

    def __str__(self):
        return self.number


class Email(models.Model):
    email = models.EmailField(verbose_name="E-Mail")
    primary = models.BooleanField(default=False, verbose_name="Primär")

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="+"
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = "E-Mail-Adresse"
        verbose_name_plural = "E-Mail-Adressen"
        ordering = ["-primary"]

    def __str__(self):
        return self.email


class BankAccount(models.Model):
    holder = models.CharField(max_length=255, verbose_name="Kontoinhaber:in")
    bank = models.CharField(max_length=255, verbose_name="Bank")
    iban = models.CharField(max_length=50, verbose_name="IBAN")

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="+"
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = "Bankverbindung"
        verbose_name_plural = "Bankverbindungen"
        ordering = ["holder"]

    def __str__(self):
        return f"{self.bank} - {self.iban}"


class Person(models.Model):
    first_name = models.CharField(max_length=255, verbose_name="Vorname")
    middle_name = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Mittlerer Name"
    )
    last_name = models.CharField(max_length=255, verbose_name="Nachname")

    full_name = models.GeneratedField(
        expression=Concat(
            F("first_name"),
            Case(
                When(
                    middle_name__isnull=False,
                    middle_name__gt="",  # Handles both NULL and empty strings
                    then=Concat(Value(" "), F("middle_name")),
                ),
                default=Value(""),
            ),
            Value(" "),
            F("last_name"),
        ),
        output_field=models.CharField(max_length=765),
        db_persist=True,
        verbose_name="Name",
    )

    phones = GenericRelation(Phone)
    emails = GenericRelation(Email)
    addresses = GenericRelation(Address)
    bank_accounts = GenericRelation(BankAccount)

    class Meta:
        verbose_name = "Person"
        verbose_name_plural = "Personen"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return self.full_name


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
