from django.utils import timezone
from django.db import models
from django.db.models import Q, F, CheckConstraint
from base.models import Person
from base.utils import COUNTRY_CHOICES, NATIONALITY_CHOICES
from base.fields import EuroDecimalField


class Denomination(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Name")

    class Meta:
        verbose_name = "Konfession"
        verbose_name_plural = "Konfessionen"
        ordering = ["name"]
        db_table = "base_denomination"

    def __str__(self):
        return self.name


class TrainingType(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Name")

    class Meta:
        verbose_name = "Fortbildungstyp"
        verbose_name_plural = "Fortbildungstypen"
        ordering = ["name"]

    def __str__(self):
        return self.name


class VocationalTraining(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Name")
    qualified = models.BooleanField(default=False, verbose_name="Qualifiziert")

    class Meta:
        verbose_name = "Berufsbildung"
        verbose_name_plural = "Berufsbildungen"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Employee(Person):
    MARITAL_STATUS_CHOICES = [
        ("single", "ledig"),
        ("married", "verheiratet"),
        ("divorced", "geschieden"),
        ("widowed", "verwitwet"),
        ("other", "sonstiges"),
    ]

    TAX_CLASS_CHOICES = [
        ("1", "Klasse 1"),
        ("2", "Klasse 2"),
        ("3", "Klasse 3"),
        ("4", "Klasse 4"),
        ("5", "Klasse 5"),
        ("6", "Klasse 6"),
    ]

    # Grunddaten (Namen sind in Person ausgelagert)
    maiden_name = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Geburtsname"
    )
    birthday = models.DateField(verbose_name="Geburtstag")
    birthplace = models.CharField(max_length=255, verbose_name="Geburtsort")
    country_of_birth = models.CharField(
        max_length=2, choices=COUNTRY_CHOICES, default="DE", verbose_name="Geburtsland"
    )
    citizenship = models.CharField(
        max_length=3,
        choices=NATIONALITY_CHOICES,
        default="000",
        verbose_name="Staatsangehörigkeit",
    )
    personnel_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Personal-Nr. Lohnprogramm",
        help_text="Personalnummer im Lohnprogramm (optional)",
    )

    # Familiärer Status
    marital_status = models.CharField(
        max_length=50, choices=MARITAL_STATUS_CHOICES, verbose_name="Familienstand"
    )
    number_of_children = models.PositiveIntegerField(
        default=0, verbose_name="Kinderzahl"
    )

    # Steuer- und Sozialversicherungsdaten
    social_security_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Sozialversicherungs-Nr.",
        help_text="12-stellige Sozialversicherungsnummer",
    )
    tax_id = models.CharField(
        max_length=50,
        verbose_name="Steuer-ID",
        help_text="11-stellige Steueridentifikationsnummer",
    )
    tax_class = models.CharField(
        max_length=10,
        choices=TAX_CLASS_CHOICES,
        blank=True,
        null=True,
        verbose_name="Steuerklasse",
    )

    # Konfession (Neue Verknüpfung)
    church_membership = models.ForeignKey(
        "Denomination",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="employees",
        verbose_name="Kirchenmitgliedschaft",
    )

    # Gesundheit und Sicherheit
    health_insurance = models.CharField(max_length=255, verbose_name="Krankenkasse")
    # GdB: Wenn NULL, liegt keine festgestellte Schwerbehinderung vor
    severe_disability_percentage = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="GdB (Prozentsatz)",
        help_text="Anerkannter GdB in Prozent. Leer lassen, wenn keine Schwerbehinderung vorliegt.",
    )
    measles_protection = models.BooleanField(
        default=False, verbose_name="Nachweis Masernschutz"
    )

    # Dokumentation
    criminal_record_certificate_date = models.DateField(
        verbose_name="Erweitertes Führungszeugnis (Datum)",
        help_text="Ausstellungsdatum des erweiterten Führungszeugnisses (§ 30a BZRG)",
    )
    risk_assessment = models.TextField(
        blank=True, null=True, verbose_name="Erläut. Gefährdungsbeurteilung"
    )

    # Allgemeine interne Daten
    lebenshilfe_start_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="Beschäftigt bei LH seit",
        help_text="Erstmaliger Beschäftigungsbeginn bei der Lebenshilfe",
    )
    vocational_trainings = models.ManyToManyField(
        VocationalTraining, blank=True, verbose_name="Berufsbildungen"
    )

    class Meta:
        verbose_name = "Angestellte:r"
        verbose_name_plural = "Angestellte"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return super().__str__()


class Employment(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="employments",
        verbose_name="Mitarbeiter:in",
    )
    start_date = models.DateField(verbose_name="Beginn Arbeitsverhältnis")
    end_date = models.DateField(
        blank=True, null=True, verbose_name="Ende Arbeitsverhältnis"
    )
    working_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Stundenumfang",
        help_text="Wöchentlicher Stundenumfang laut Arbeitsvertrag",
    )

    class Meta:
        verbose_name = "Arbeitsverhältnis"
        verbose_name_plural = "Arbeitsverhältnisse"
        ordering = ["-start_date"]
        constraints = [
            CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="employment_end_date_after_start_date",
            )
        ]

    def __str__(self):
        end = self.end_date.strftime("%d.%m.%Y") if self.end_date else "laufend"
        return f"Arbeitsverhältnis {self.employee.full_name} ({self.start_date.strftime('%d.%m.%Y')} - {end})"


class OtherEmployment(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="other_employments",
        verbose_name="Mitarbeiter:in",
    )
    employer = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Arbeitgeber (Sonstige)"
    )
    working_hours = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name="Stundenumfang"
    )

    class Meta:
        verbose_name = "Weiteres Arbeitsverhältnis"
        verbose_name_plural = "Weitere Arbeitsverhältnisse"
        ordering = ["employee__last_name", "employee__first_name", "employer"]

    def __str__(self):
        return f"{self.employer or 'Unbekannter Arbeitgeber'} ({self.working_hours}h) - {self.employee.full_name}"


class Applicant(Person):
    application_date = models.DateField(verbose_name="Datum der Bewerbung")
    desired_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Stundenwunsch",
    )
    desired_school = models.ForeignKey(
        "pedagogy.School",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="applicants",
        verbose_name="Schulwunsch",
    )
    notice_period = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Kündigungsfristen"
    )
    suitability_rating = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="Einstufung nach Eignung"
    )

    class Meta:
        verbose_name = "Bewerber:in"
        verbose_name_plural = "Bewerber:innen"
        ordering = ["-application_date"]

    def __str__(self):
        return super().__str__()


class Absence(models.Model):
    REASON_CHOICES = [
        ("illness", "Krankheit"),
        ("child_sick", "Kind krank"),
        ("appointment", "Termin"),
        ("other", "Sonstiges"),
    ]
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="absences",
        verbose_name="Mitarbeiter:in",
    )
    start_date = models.DateField(blank=True, null=True, db_index=True, verbose_name="Beginn")
    end_date = models.DateField(blank=True, null=True, verbose_name="Ende")
    reason = models.CharField(
        max_length=50, choices=REASON_CHOICES, verbose_name="Grund"
    )
    certificate = models.BooleanField(
        default=False,
        verbose_name="Mit AU",
        help_text="Liegt eine ärztliche Arbeitsunfähigkeitsbescheinigung vor?",
    )

    class Meta:
        verbose_name = "Abwesenheit"
        verbose_name_plural = "Abwesenheiten"
        ordering = ["-start_date"]
        constraints = [
            CheckConstraint(
                condition=Q(start_date__isnull=True)
                | Q(end_date__isnull=True)
                | Q(end_date__gte=F("start_date")),
                name="absence_end_after_start",
            )
        ]

    def __str__(self):
        return f"Abwesenheit: {self.employee.full_name} ({self.get_reason_display()})"


class TrainingRecord(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="training_records",
        verbose_name="Mitarbeiter:in",
    )
    training_type = models.ForeignKey(
        TrainingType,
        on_delete=models.PROTECT,
        related_name="training_records",
        verbose_name="Fortbildungstyp",
    )
    valid_from = models.DateField(db_index=True, verbose_name="Gültig von")
    valid_to = models.DateField(
        blank=True,
        null=True,
        verbose_name="Gültig bis",
        help_text="Leer lassen, wenn die Fortbildung dauerhaft gültig ist",
    )

    class Meta:
        verbose_name = "Fortbildungsnachweis"
        verbose_name_plural = "Fortbildungsnachweise"
        ordering = ["-valid_from"]
        constraints = [
            CheckConstraint(
                condition=Q(valid_to__isnull=True) | Q(valid_to__gte=F("valid_from")),
                name="trainingrecord_valid_to_after_valid_from",
            )
        ]

    @property
    def is_valid(self):
        today = timezone.now().date()
        starts_ok = self.valid_from <= today
        ends_ok = self.valid_to is None or self.valid_to >= today
        return starts_ok and ends_ok

    def __str__(self):
        return f"Fortbildung {self.training_type} für {self.employee.full_name}"
