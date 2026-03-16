from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from phonenumber_field.modelfields import PhoneNumberField

class Denomination(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Name")

    class Meta:
        verbose_name = "Konfession"
        verbose_name_plural = "Konfessionen"
        ordering = ['name']

    def __str__(self):
        return self.name

class Address(models.Model):
    primary = models.BooleanField(default=False, verbose_name="Primär")
    street = models.CharField(max_length=255, verbose_name="Straße")
    house_number = models.CharField(max_length=50, verbose_name="Hausnummer")
    postcode = models.PositiveIntegerField(verbose_name="Postleitzahl")
    city = models.CharField(max_length=255, verbose_name="Stadt")
    district = models.CharField(max_length=255, blank=True, null=True, verbose_name="Ortsteil")
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "Adresse"
        verbose_name_plural = "Adressen"

    def __str__(self):
        ort = f"{self.postcode} {self.city}"
        if self.district:
            ort += f" ({self.district})"
        return f"{self.street} {self.house_number}, {ort}"

class Phone(models.Model):
    telephone_number = PhoneNumberField(region="DE", verbose_name="Telefonnummer")
    primary = models.BooleanField(default=False, verbose_name="Primär")
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "Telefonnummer"
        verbose_name_plural = "Telefonnummern"

    def __str__(self):
        return self.telephone_number

class Email(models.Model):
    email = models.EmailField(verbose_name="E-Mail")
    primary = models.BooleanField(default=False, verbose_name="Primär")
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "E-Mail-Adresse"
        verbose_name_plural = "E-Mail-Adressen"

    def __str__(self):
        return self.email

class BankAccount(models.Model):
    holder = models.CharField(max_length=255, verbose_name="Kontoinhaber:in")
    bank = models.CharField(max_length=255, verbose_name="Bank")
    iban = models.CharField(max_length=50, verbose_name="IBAN")
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "Bankverbindung"
        verbose_name_plural = "Bankverbindungen"

    def __str__(self):
        return f"{self.bank} - {self.iban}"

class ExternalIdentifier(models.Model):
    label = models.CharField(max_length=255, verbose_name="Bezeichnung")
    value = models.CharField(max_length=255, verbose_name="Nummer/Wert")
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "Identifikator"
        verbose_name_plural = "Identifikatoren"

    def __str__(self):
        return f"{self.label}: {self.value}"

class CostPayerLink(models.Model):
    primary = models.BooleanField(default=False, verbose_name="Primär")
    identifier = models.ForeignKey('finance.CostPayer', on_delete=models.PROTECT, verbose_name="Kostenzahler")
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = "Kostenzahler-Verknüpfung"
        verbose_name_plural = "Kostenzahler-Verknüpfungen"

    def __str__(self):
        return str(self.identifier)

class Person(models.Model):
    first_name = models.CharField(max_length=255, verbose_name="Vorname")
    middle_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Mittlerer Name")
    last_name = models.CharField(max_length=255, verbose_name="Nachname")

    phones = GenericRelation(Phone)
    emails = GenericRelation(Email)
    addresses = GenericRelation(Address)
    bank_accounts = GenericRelation(BankAccount)

    class Meta:
        verbose_name = "Person"
        verbose_name_plural = "Personen"

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join([p for p in parts if p])

    def __str__(self):
        return self.full_name

class MasterData(models.Model):
    identifiers = GenericRelation(ExternalIdentifier)
    accounts = GenericRelation(BankAccount)

    class Meta:
        verbose_name = "Stammdaten"
        verbose_name_plural = "Stammdaten"

    def __str__(self):
        return f"Stammdaten: {self.name}"
