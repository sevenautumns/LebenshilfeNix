from decimal import Decimal
from datetime import timedelta
from django.db import models
from django.db.models import Q, F, CheckConstraint
from base.models import Person, SchoolDays
from base.fields import HourMinuteDurationField


class School(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Name")

    class Meta:
        verbose_name = "Schule"
        verbose_name_plural = "Schulen"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Student(Person):
    payer = models.ForeignKey(
        "finance.CostPayer",
        on_delete=models.PROTECT,
        related_name="students",
        verbose_name="Kostenträger",
    )

    class Meta:
        verbose_name = "Schüler:in"
        verbose_name_plural = "Schüler:innen"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return super().__str__()


class Supervision(models.Model):
    student = models.ForeignKey(
        Student,
        related_name="supervisions",
        on_delete=models.PROTECT,
        verbose_name="Schüler:in",
    )
    is_prophylactic = models.BooleanField(
        default=False,
        verbose_name="Prophylaktisch",
    )
    tandem = models.ForeignKey(
        Student,
        related_name="tandem_supervisions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Tandem",
    )
    is_tandem_prophylactic = models.BooleanField(
        default=False,
        verbose_name="Tandem prophylaktisch",
    )
    caretaker = models.ForeignKey(
        "hr.Employee",
        on_delete=models.PROTECT,
        related_name="supervisions",
        verbose_name="Betreuer:in",
    )
    class_name = models.CharField(max_length=100, blank=True, verbose_name="Klasse")
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name="supervisions",
        verbose_name="Schule",
    )
    start_date = models.DateField(verbose_name="Beginn")
    end_date = models.DateField(verbose_name="Ende")
    weekly_hours = HourMinuteDurationField(verbose_name="Wochenstunden")
    school_days_override = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Schultage (Überschreibung)",
        help_text="Überschreibt die Schultage aus den Stammdaten für diese Betreuung",
    )

    class Meta:
        verbose_name = "Betreuung"
        verbose_name_plural = "Betreuungen"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["start_date"], name="supervision_start_date_idx"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="supervision_end_after_start",
            )
        ]

    @property
    def calculated_school_days(self) -> int:
        return SchoolDays.total_school_days(self.start_date, self.end_date)

    calculated_school_days.fget.short_description = "Schultage (rechnerisch)"  # type: ignore[attr-defined]

    @property
    def daily_hours(self) -> timedelta | None:
        if self.weekly_hours is None:
            return None
        return self.weekly_hours / 5

    daily_hours.fget.short_description = "Stunden pro Tag"  # type: ignore[attr-defined]

    @property
    def total_hours(self) -> timedelta | None:
        if self.daily_hours is None:
            return None
        days = (
            self.school_days_override
            if self.school_days_override is not None
            else self.calculated_school_days
        )
        return self.daily_hours * days

    total_hours.fget.short_description = "Gesamtstunden"  # type: ignore[attr-defined]

    @property
    def fee_agreement(self):
        from finance.models import FeeAgreement

        return FeeAgreement.objects.filter(
            Q(responsible_payer=self.student.payer)
            | Q(additional_payers=self.student.payer),
            valid_from__lte=self.start_date,
            valid_to__gte=self.start_date,
        ).first()

    fee_agreement.fget.short_description = "Entgeltvereinbarung"  # type: ignore[attr-defined]

    @property
    def total_amount(self) -> Decimal | None:
        fee = self.fee_agreement
        if fee is None:
            return None
        price = fee.price_tandem if self.tandem_id else fee.price_standard
        return price * Decimal(self.total_hours.total_seconds() / 3600)

    total_amount.fget.short_description = "Gesamtbetrag"  # type: ignore[attr-defined]

    @property
    def monthly_installment(self) -> Decimal | None:
        amount = self.total_amount
        if amount is None:
            return None
        months = (
            (self.end_date.year - self.start_date.year) * 12
            + self.end_date.month
            - self.start_date.month
            + 1
        )
        return amount / months

    monthly_installment.fget.short_description = "Abschlag pro Monat"  # type: ignore[attr-defined]

    def save(self, *args: object, **kwargs: object) -> None:
        if not self.tandem_id:
            self.is_tandem_prophylactic = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Betreuung {self.student.full_name} durch {self.caretaker.full_name}"


class Request(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        IN_COORDINATION = "in_coordination", "In Abstimmung"
        REJECTED = "rejected", "Abgelehnt"
        APPROVED = "approved", "Genehmigt"

    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="requests",
        verbose_name="Schüler:in",
    )
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name="requests",
        verbose_name="Schule",
    )
    start_date = models.DateField(verbose_name="Beginn")
    end_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Gültig bis",
        help_text="Ende der Bewilligungsperiode. Leer lassen, wenn unbefristet.",
    )
    review_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Überprüfung geplant bis",
    )
    demand = HourMinuteDurationField(
        verbose_name="Betreuungsbedarf pro Woche",
        help_text="Genehmigter wöchentlicher Betreuungsumfang",
    )
    state = models.CharField(
        max_length=50,
        choices=State.choices,
        default=State.DRAFT,
        verbose_name="Zustand",
    )
    notes = models.TextField(blank=True, verbose_name="Notizen")

    class Meta:
        verbose_name = "Antrag"
        verbose_name_plural = "Anträge"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["start_date"], name="request_start_date_idx"),
            models.Index(fields=["state"], name="request_state_idx"),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="request_end_date_after_start_date",
            )
        ]

    def __str__(self):
        return f"Antrag: {self.student.full_name} ({self.get_state_display()})"
