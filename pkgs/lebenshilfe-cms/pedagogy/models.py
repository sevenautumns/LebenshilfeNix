from django.db import models
from base.models import Person


class School(models.Model):
    school_name = models.CharField(max_length=255, unique=True, verbose_name="Name")

    class Meta:
        verbose_name = "Schule"
        verbose_name_plural = "Schulen"

    def __str__(self):
        return self.school_name


class Student(Person):
    payer = models.ForeignKey(
        "finance.CostPayer", on_delete=models.PROTECT, verbose_name="Kostenzahler"
    )

    class Meta:
        verbose_name = "Schulkind"
        verbose_name_plural = "Schulkinder"

    def __str__(self):
        return super().__str__()


class Supervision(models.Model):
    student = models.ForeignKey(
        Student,
        related_name="supervisions",
        on_delete=models.PROTECT,
        verbose_name="Schulkind",
    )
    tandem = models.ForeignKey(
        Student,
        related_name="tandem_supervisions",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Tandem",
    )
    caretaker = models.ForeignKey(
        "hr.Employee", on_delete=models.PROTECT, verbose_name="Betreuer:in"
    )
    class_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Klasse"
    )
    school = models.ForeignKey(School, on_delete=models.PROTECT, verbose_name="Schule")
    start = models.DateField(verbose_name="Beginn")
    end = models.DateField(verbose_name="Ende")
    weekly_hours = models.DurationField(verbose_name="Wochenstunden")
    school_days = models.PositiveIntegerField(verbose_name="Schultage")

    class Meta:
        verbose_name = "Betreuung"
        verbose_name_plural = "Betreuungen"

    def __str__(self):
        return f"Betreuung {self.student.full_name} durch {self.caretaker.full_name}"


class Request(models.Model):
    STATE_CHOICES = [
        ("draft", "Entwurf"),
        ("in_coordination", "In Abstimmung"),
        ("rejected", "Abgelehnt"),
        ("approved", "Genehmigt"),
    ]
    student = models.ForeignKey(
        Student, on_delete=models.PROTECT, verbose_name="Schulkind"
    )
    school = models.ForeignKey(School, on_delete=models.PROTECT, verbose_name="Schule")
    start = models.DateField(verbose_name="Beginn")
    valid_to = models.DateField(blank=True, null=True, verbose_name="Gültig bis")
    demand = models.DurationField(verbose_name="Betreuungsbedarf pro Woche")
    state = models.CharField(
        max_length=50, choices=STATE_CHOICES, default="draft", verbose_name="Zustand"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Notizen")

    class Meta:
        verbose_name = "Antrag"
        verbose_name_plural = "Anträge"

    def __str__(self):
        return f"Antrag: {self.student.full_name} ({self.get_state_display()})"
