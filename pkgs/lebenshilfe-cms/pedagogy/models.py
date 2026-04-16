from datetime import timedelta
from django.db import models
from django.db.models import Q, F, CheckConstraint
from base.models import AbstractContact, Person, SchoolDays
from base.fields import EuroDecimalField, HourMinuteDurationField


class School(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Name")

    # Adresse (optional)
    street = models.CharField(max_length=255, blank=True, verbose_name="Straße")
    house_number = models.CharField(
        max_length=50, blank=True, verbose_name="Hausnummer"
    )
    postcode = models.CharField(max_length=10, blank=True, verbose_name="PLZ")
    city = models.CharField(max_length=255, blank=True, verbose_name="Ort")
    district = models.CharField(max_length=255, blank=True, verbose_name="Ortsteil")

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
    total_amount = EuroDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Gesamtbetrag",
    )
    monthly_installment = EuroDecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Abschlag pro Monat",
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
    def calculated_months(self) -> int:
        from pedagogy.calculators import calculate_supervision_months

        return calculate_supervision_months(self.start_date, self.end_date)

    calculated_months.fget.short_description = "Monate (rechnerisch)"  # type: ignore[attr-defined]

    def __str__(self):
        return f"Betreuung {self.student.full_name} durch {self.caretaker.full_name}"


class Request(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        IN_REVIEW = "in_review", "In Prüfung"
        REJECTED = "rejected", "Abgelehnt"
        APPROVED = "approved", "Genehmigt"

    class ApprovalType(models.TextChoices):
        PHONE = "phone", "Telefonisch"
        EMAIL = "email", "Per Mail"
        NOTICE = "notice", "Per Bescheid"

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
    decision_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Entscheidungsdatum",
        help_text="Datum der Genehmigung oder Ablehnung.",
    )
    approval_type = models.CharField(
        max_length=20,
        choices=ApprovalType.choices,
        blank=True,
        verbose_name="Art der Genehmigung",
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


class TandemPairing(models.Model):
    supervision_a = models.OneToOneField(
        Supervision,
        on_delete=models.PROTECT,
        related_name="tandem_as_a",
        verbose_name="Betreuung A",
    )
    supervision_b = models.OneToOneField(
        Supervision,
        on_delete=models.PROTECT,
        related_name="tandem_as_b",
        verbose_name="Betreuung B",
    )

    class Meta:
        verbose_name = "Tandembetreuung"
        verbose_name_plural = "Tandembetreuungen"

    def __str__(self):
        return f"Tandem: {self.supervision_a.student} & {self.supervision_b.student}"

    @property
    def caretaker_matches(self) -> bool:
        return self.supervision_a.caretaker_id == self.supervision_b.caretaker_id

    caretaker_matches.fget.short_description = "Betreuer stimmt überein"  # type: ignore[attr-defined]

    @property
    def hours_match(self) -> bool:
        return self.supervision_a.weekly_hours == self.supervision_b.weekly_hours

    hours_match.fget.short_description = "Stunden stimmen überein"  # type: ignore[attr-defined]


class SchoolReport(Supervision):
    class Meta:
        proxy = True
        verbose_name = "Schulauswertung"
        verbose_name_plural = "Schulauswertungen"


class NewRequest(Supervision):
    class Meta:
        proxy = True
        verbose_name = "Neuantrag"
        verbose_name_plural = "Neuanträge"


class SchoolContact(AbstractContact):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="contacts",
        verbose_name="Schule",
    )

    class Meta(AbstractContact.Meta):
        verbose_name = "Ansprechperson"
        verbose_name_plural = "Ansprechpersonen"
