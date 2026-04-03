import calendar
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db import models
from django.db.models import Q, F, CheckConstraint
from base.models import Person, SchoolDays
from base.choices import CountryChoices, NationalityChoices
from base.fields import EuroDecimalField, HourMinuteDurationField


class Denomination(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Name")

    class Meta:
        verbose_name = "Konfession"
        verbose_name_plural = "Konfessionen"
        ordering = ["name"]

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
    class MaritalStatus(models.TextChoices):
        SINGLE = "single", "ledig"
        MARRIED = "married", "verheiratet"
        DIVORCED = "divorced", "geschieden"
        WIDOWED = "widowed", "verwitwet"
        OTHER = "other", "sonstiges"

    class TaxClass(models.TextChoices):
        CLASS_1 = "1", "Klasse 1"
        CLASS_2 = "2", "Klasse 2"
        CLASS_3 = "3", "Klasse 3"
        CLASS_4 = "4", "Klasse 4"
        CLASS_5 = "5", "Klasse 5"
        CLASS_6 = "6", "Klasse 6"

    # Grunddaten (Namen sind in Person ausgelagert)
    maiden_name = models.CharField(
        max_length=255, blank=True, verbose_name="Geburtsname"
    )
    birthday = models.DateField(blank=True, null=True, verbose_name="Geburtstag")
    birthplace = models.CharField(max_length=255, blank=True, verbose_name="Geburtsort")
    country_of_birth = models.CharField(
        max_length=2,
        choices=CountryChoices.choices,
        blank=True,
        null=True,
        verbose_name="Geburtsland",
    )
    citizenship = models.CharField(
        max_length=3,
        choices=NationalityChoices.choices,
        blank=True,
        null=True,
        verbose_name="Staatsangehörigkeit",
    )
    personnel_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Personal-Nr. Lohnprogramm",
        help_text="Personalnummer im Lohnprogramm (optional)",
    )

    # Familiärer Status
    marital_status = models.CharField(
        max_length=50,
        choices=MaritalStatus.choices,
        blank=True,
        verbose_name="Familienstand",
    )
    number_of_children = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Kinderzahl"
    )

    # Steuer- und Sozialversicherungsdaten
    social_security_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Sozialversicherungs-Nr.",
        help_text="12-stellige Sozialversicherungsnummer",
    )
    tax_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Steuer-ID",
        help_text="11-stellige Steueridentifikationsnummer",
    )
    tax_class = models.CharField(
        max_length=10,
        choices=TaxClass.choices,
        blank=True,
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
    health_insurance = models.CharField(
        max_length=255, blank=True, verbose_name="Krankenkasse"
    )
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
        blank=True,
        null=True,
        verbose_name="Erweitertes Führungszeugnis (Datum)",
        help_text="Ausstellungsdatum des erweiterten Führungszeugnisses (§ 30a BZRG)",
    )
    risk_assessment = models.TextField(
        blank=True, verbose_name="Erläut. Gefährdungsbeurteilung"
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
        indexes = [
            models.Index(
                fields=["personnel_number"], name="employee_personnel_number_idx"
            ),
        ]

    def __str__(self):
        return super().__str__()


class Employment(models.Model):
    class ContractType(models.TextChoices):
        SCHOOL_ACCOMPANIMENT = "school_accompaniment", "Schulbegleitung"
        TANDEM = "tandem", "Tandem"
        SCHOOL_ACCOMPANIMENT_HONORARY = (
            "school_accompaniment_honorary",
            "Schulbegleitung (Ehrenamt)",
        )
        TANDEM_HONORARY = "tandem_honorary", "Tandem (Ehrenamt)"
        COORDINATION = "coordination", "Koordination"
        MANAGEMENT = "management", "Geschäftsleitung"

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
    weekly_hours = HourMinuteDurationField(
        verbose_name="Wochenstunden",
        help_text="Wöchentlicher Stundenumfang laut Arbeitsvertrag",
    )
    contract_type = models.CharField(
        max_length=50,
        choices=ContractType.choices,
        blank=True,
        verbose_name="Art des Vertrags",
    )
    gross_salary_override = EuroDecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Brutto laut Vertrag (Überschreibung)",
        help_text="Überschreibt das Brutto laut Vertrag pro Monat für dieses Arbeitsverhältnis",
    )
    work_days_override = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Arbeitstage (Überschreibung)",
        help_text="Überschreibt die Arbeitstage aus den Stammdaten für dieses Arbeitsverhältnis",
    )
    month_override = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Monate (Überschreibung)",
        help_text="Überschreibt die rechnerischen Vertragsmonate für dieses Arbeitsverhältnis",
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

    @property
    def calculated_work_days(self) -> int | None:
        if self.end_date is None:
            return None
        return SchoolDays.total_school_days(self.start_date, self.end_date)

    @property
    def daily_hours(self) -> timedelta | None:
        if self.weekly_hours is None:
            return None
        return self.weekly_hours / 5

    @property
    def calculated_months(self) -> Decimal | None:
        if self.end_date is None:
            return None
        whole_months = (self.end_date.year - self.start_date.year) * 12 + (
            self.end_date.month - self.start_date.month
        )
        day_diff = self.end_date.day - self.start_date.day
        if day_diff >= 0:
            days_in_month = calendar.monthrange(
                self.end_date.year, self.end_date.month
            )[1]
            fraction = Decimal(day_diff) / Decimal(days_in_month)
        else:
            whole_months -= 1
            prev_month = self.end_date.month - 1 or 12
            prev_year = (
                self.end_date.year
                if self.end_date.month > 1
                else self.end_date.year - 1
            )
            days_in_month = calendar.monthrange(prev_year, prev_month)[1]
            fraction = Decimal(days_in_month + day_diff) / Decimal(days_in_month)
        return (Decimal(whole_months) + fraction).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    @property
    def _effective_months(self) -> Decimal | None:
        return (
            self.month_override
            if self.month_override is not None
            else self.calculated_months
        )

    @property
    def yearly_hours(self) -> timedelta | None:
        work_days = (
            self.work_days_override
            if self.work_days_override is not None
            else self.calculated_work_days
        )
        if work_days is None or self.daily_hours is None:
            return None
        return self.daily_hours * work_days

    @property
    def monthly_hours(self) -> Decimal | None:
        months = self._effective_months
        if self.yearly_hours is None or not months:
            return None
        return Decimal(self.yearly_hours.total_seconds() / 3600) / months

    @property
    def salary_agreement(self):
        from finance.models import SalaryAgreement

        return SalaryAgreement.objects.filter(
            valid_from__lte=self.start_date,
            valid_to__gte=self.start_date,
        ).first()

    @property
    def calculated_gross_salary(self) -> Decimal | None:
        if self.gross_salary_override is not None:
            return self.gross_salary_override
        if self.monthly_hours is None:
            return None
        agreement = self.salary_agreement
        if not agreement or not self.contract_type:
            return None
        rate_map = {
            Employment.ContractType.SCHOOL_ACCOMPANIMENT: agreement.salary_standard,
            Employment.ContractType.TANDEM: agreement.salary_tandem,
            Employment.ContractType.SCHOOL_ACCOMPANIMENT_HONORARY: agreement.salary_honorary_standard,
            Employment.ContractType.TANDEM_HONORARY: agreement.salary_honorary_tandem,
            Employment.ContractType.COORDINATION: agreement.salary_coordination,
            Employment.ContractType.MANAGEMENT: agreement.salary_management,
        }
        rate = rate_map.get(self.contract_type)
        if rate is None:
            return None
        return (rate * self.monthly_hours).quantize(
            Decimal("1E+1"), rounding=ROUND_HALF_UP
        )

    @property
    def yearly_gross_salary(self) -> Decimal | None:
        gross = self.calculated_gross_salary
        months = self._effective_months
        if gross is None or months is None:
            return None
        return gross * months


class OtherEmployment(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="other_employments",
        verbose_name="Mitarbeiter:in",
    )
    employer = models.CharField(
        max_length=255, blank=True, verbose_name="Arbeitgeber (Sonstige)"
    )
    weekly_hours = HourMinuteDurationField(verbose_name="Stundenumfang")

    class Meta:
        verbose_name = "Weiteres Arbeitsverhältnis"
        verbose_name_plural = "Weitere Arbeitsverhältnisse"
        ordering = ["employee__last_name", "employee__first_name", "employer"]

    def __str__(self):
        hours_str = OtherEmployment.weekly_hours.field.get_admin_format(
            self.weekly_hours
        )
        return f"{self.employer or 'Unbekannter Arbeitgeber'} ({hours_str}) - {self.employee.full_name}"


class Applicant(Person):
    application_date = models.DateField(verbose_name="Datum der Bewerbung")
    desired_hours_min = HourMinuteDurationField(
        blank=True,
        null=True,
        verbose_name="Stundenwunsch (von)",
    )
    desired_hours_max = HourMinuteDurationField(
        blank=True,
        null=True,
        verbose_name="Stundenwunsch (bis)",
    )
    desired_school = models.ForeignKey(
        "pedagogy.School",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="applicants",
        verbose_name="Schulwunsch",
    )
    notice_period_months = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name="Kündigungsfrist (Monate)",
        help_text="Kündigungsfrist in Monaten, z. B. 1.0 = 1 Monat, 3.0 = 3 Monate.",
    )
    earliest_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Frühestmöglicher Eintrittstermin",
    )

    class Meta:
        verbose_name = "Bewerber:in"
        verbose_name_plural = "Bewerber:innen"
        ordering = ["-application_date"]

    def __str__(self):
        return super().__str__()

    @property
    def desired_hours_summary(self) -> str:
        def fmt(td) -> str:
            h, m = HourMinuteDurationField.to_hours_minutes(td)
            return f"{h}:{m:02d}"

        mn, mx = self.desired_hours_min, self.desired_hours_max
        if mn is not None and mx is not None:
            return f"{fmt(mn)}–{fmt(mx)} Std."
        if mn is not None:
            return f"ab {fmt(mn)} Std."
        if mx is not None:
            return f"bis {fmt(mx)} Std."
        return "–"


class Absence(models.Model):
    class Reason(models.TextChoices):
        ILLNESS = "illness", "Krankheit"
        CHILD_SICK = "child_sick", "Kind krank"
        APPOINTMENT = "appointment", "Termin"
        OTHER = "other", "Sonstiges"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="absences",
        verbose_name="Mitarbeiter:in",
    )
    start_date = models.DateField(blank=True, null=True, verbose_name="Beginn")
    end_date = models.DateField(blank=True, null=True, verbose_name="Ende")
    reason = models.CharField(
        max_length=50, choices=Reason.choices, verbose_name="Grund"
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
        indexes = [
            models.Index(fields=["start_date"], name="absence_start_date_idx"),
        ]
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
    valid_from = models.DateField(verbose_name="Gültig von")
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
        indexes = [
            models.Index(fields=["valid_from"], name="trainingrecord_valid_from_idx"),
        ]
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
