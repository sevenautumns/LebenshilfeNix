from django.utils import timezone
from django.db import models
from base.models import Person
from base.utils import COUNTRY_CHOICES, NATIONALITY_CHOICES


class TrainingType(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Name")

    class Meta:
        verbose_name = "Fortbildungstyp"
        verbose_name_plural = "Fortbildungstypen"

    def __str__(self):
        return self.name


class VocationalTraining(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Name")
    qualified = models.BooleanField(default=False, verbose_name="Qualifiziert")

    class Meta:
        verbose_name = "Berufsbildung"
        verbose_name_plural = "Berufsbildungen"

    def __str__(self):
        return self.name


class SalaryAgreement(models.Model):
    salary_standard = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Schulbegleitung (allgemein)"
    )
    salary_tandem = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Tandem"
    )
    salary_coordination = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Koordination"
    )
    salary_management = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Geschäftsführung"
    )
    valid_from = models.DateField(verbose_name="Gültig von")
    valid_to = models.DateField(verbose_name="Gültig bis")

    class Meta:
        verbose_name = "Gehaltsvereinbarung"
        verbose_name_plural = "Gehaltsvereinbarungen"

    def __str__(self):
        return f"Gehaltsvereinbarung ({self.valid_from} - {self.valid_to})"


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
        max_length=50, blank=True, null=True, verbose_name="Personal-Nr. Lohnprogramm"
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
        max_length=50, blank=True, null=True, verbose_name="Sozialversicherungs-Nr."
    )
    tax_id = models.CharField(max_length=50, verbose_name="Steuer-ID")
    tax_class = models.CharField(
        max_length=10,
        choices=TAX_CLASS_CHOICES,
        blank=True,
        null=True,
        verbose_name="Steuerklasse",
    )

    # Konfession (Neue Verknüpfung)
    church_membership = models.ForeignKey(
        "base.Denomination",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Kirchenmitgliedschaft",
    )

    # Gesundheit und Sicherheit
    health_insurance = models.CharField(max_length=255, verbose_name="Krankenkasse")
    # GdB: Wenn NULL, liegt keine festgestellte Schwerbehinderung vor
    severe_disability_percentage = models.PositiveIntegerField(
        blank=True, null=True, verbose_name="GdB (Prozentsatz)"
    )
    measles_protection = models.BooleanField(
        default=False, verbose_name="Nachweis Masernschutz"
    )

    # Dokumentation
    criminal_record_certificate = models.DateField(
        verbose_name="Erweitertes Führungszeugnis (Datum)"
    )
    risk_assessment = models.TextField(
        blank=True, null=True, verbose_name="Erläut. Gefährdungsbeurteilung"
    )

    # Allgemeine interne Daten
    lh_start = models.DateField(
        blank=True, null=True, verbose_name="Beschäftigt bei LH seit"
    )
    vocational_trainings = models.ManyToManyField(
        VocationalTraining, blank=True, verbose_name="Berufsbildungen"
    )

    class Meta:
        verbose_name = "Angestellte:r"
        verbose_name_plural = "Angestellte"

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
        max_digits=5, decimal_places=2, verbose_name="Stundenumfang"
    )

    class Meta:
        verbose_name = "Arbeitsverhältnis"
        verbose_name_plural = "Arbeitsverhältnisse"

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

    def __str__(self):
        return super().__str__()


class Absence(models.Model):
    REASON_CHOICES = [
        ("illness", "Krankheit"),
        ("child_sick", "Kind Krank"),
        ("appointment", "Termin"),
        ("other", "Sonstiges"),
    ]
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, verbose_name="Mitarbeiter:in"
    )
    start = models.DateField(blank=True, null=True, verbose_name="Beginn")
    end = models.DateField(blank=True, null=True, verbose_name="Ende")
    reason = models.CharField(
        max_length=50, choices=REASON_CHOICES, verbose_name="Grund"
    )
    certificate = models.BooleanField(default=False, verbose_name="Mit AU")

    class Meta:
        verbose_name = "Abwesenheit"
        verbose_name_plural = "Abwesenheiten"

    def __str__(self):
        return f"Abwesenheit: {self.employee.full_name} ({self.get_reason_display()})"


class TrainingRecord(models.Model):
    staff = models.ForeignKey(
        Employee, on_delete=models.PROTECT, verbose_name="Personalfall"
    )
    training_type = models.ForeignKey(
        TrainingType, on_delete=models.PROTECT, verbose_name="Fortbildungstyp"
    )
    valid_from = models.DateField(verbose_name="Gültig von")
    valid_to = models.DateField(blank=True, null=True, verbose_name="Gültig bis")

    class Meta:
        verbose_name = "Fortbildungsnachweis"
        verbose_name_plural = "Fortbildungsnachweise"

    @property
    def is_valid(self):
        today = timezone.now().date()
        starts_ok = self.valid_from <= today
        ends_ok = self.valid_to is None or self.valid_to >= today
        return starts_ok and ends_ok

    def __str__(self):
        return f"Fortbildung {self.training_type} für {self.staff.full_name}"
