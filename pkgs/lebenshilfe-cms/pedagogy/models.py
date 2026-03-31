from django.db import models
from django.db.models import Q, F, CheckConstraint
from base.models import Person
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
    class_name = models.CharField(
        max_length=100, blank=True, verbose_name="Klasse"
    )
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
    is_prophylactic = models.BooleanField(
        default=False,
        verbose_name="Prophylaktisch",
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
        max_length=50, choices=State.choices, default=State.DRAFT, verbose_name="Zustand"
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
