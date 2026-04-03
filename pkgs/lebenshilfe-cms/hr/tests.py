from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from base.models import SchoolDays
from finance.models import SalaryAgreement
from hr.models import Applicant, Employee, Employment, TrainingRecord, TrainingType


# --- TrainingRecord.is_valid Tests ---


class TrainingRecordTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(first_name="Max", last_name="Muster")
        self.training_type = TrainingType.objects.create(name="Erste Hilfe")
        self.today = date.today()

    def _make_record(self, valid_from, valid_to=None):
        return TrainingRecord(
            employee=self.employee,
            training_type=self.training_type,
            valid_from=valid_from,
            valid_to=valid_to,
        )

    def test_is_valid_current(self):
        """Ein Nachweis mit Vergangenheit als Start und Zukunft als Ende ist gültig."""
        record = self._make_record(
            valid_from=self.today - timedelta(days=365),
            valid_to=self.today + timedelta(days=365),
        )
        self.assertTrue(record.is_valid)

    def test_is_valid_permanent(self):
        """Ein Nachweis ohne Enddatum ist dauerhaft gültig."""
        record = self._make_record(
            valid_from=self.today - timedelta(days=100),
            valid_to=None,
        )
        self.assertTrue(record.is_valid)

    def test_is_valid_expired(self):
        """Ein Nachweis, dessen Enddatum gestern war, ist nicht mehr gültig."""
        record = self._make_record(
            valid_from=self.today - timedelta(days=365),
            valid_to=self.today - timedelta(days=1),
        )
        self.assertFalse(record.is_valid)

    def test_is_valid_not_yet_started(self):
        """Ein Nachweis, der erst morgen beginnt, ist noch nicht gültig."""
        record = self._make_record(
            valid_from=self.today + timedelta(days=1),
            valid_to=self.today + timedelta(days=365),
        )
        self.assertFalse(record.is_valid)

    def test_is_valid_expires_today(self):
        """Ein Nachweis, der heute ausläuft, ist noch gültig (inklusiv)."""
        record = self._make_record(
            valid_from=self.today - timedelta(days=365),
            valid_to=self.today,
        )
        self.assertTrue(record.is_valid)

    def test_is_valid_starts_today(self):
        """Ein Nachweis, der heute beginnt, ist bereits gültig (inklusiv)."""
        record = self._make_record(
            valid_from=self.today,
            valid_to=self.today + timedelta(days=365),
        )
        self.assertTrue(record.is_valid)


# --- Applicant.desired_hours_summary Tests ---


class ApplicantDesiredHoursTests(TestCase):
    def _make_applicant(self, min_hours=None, max_hours=None):
        return Applicant(
            first_name="Test",
            last_name="Person",
            application_date=date.today(),
            desired_hours_min=min_hours,
            desired_hours_max=max_hours,
        )

    def test_both_min_and_max(self):
        """Prüft die Ausgabe, wenn Min und Max gesetzt sind."""
        applicant = self._make_applicant(
            min_hours=timedelta(hours=2),
            max_hours=timedelta(hours=4),
        )
        self.assertEqual(applicant.desired_hours_summary, "2:00–4:00 Std.")

    def test_only_min(self):
        """Prüft die Ausgabe, wenn nur ein Mindestwert gesetzt ist."""
        applicant = self._make_applicant(min_hours=timedelta(hours=2))
        self.assertEqual(applicant.desired_hours_summary, "ab 2:00 Std.")

    def test_only_max(self):
        """Prüft die Ausgabe, wenn nur ein Maximalwert gesetzt ist."""
        applicant = self._make_applicant(max_hours=timedelta(hours=4))
        self.assertEqual(applicant.desired_hours_summary, "bis 4:00 Std.")

    def test_neither(self):
        """Prüft die Ausgabe, wenn kein Stundenwunsch angegeben ist."""
        applicant = self._make_applicant()
        self.assertEqual(applicant.desired_hours_summary, "–")

    def test_minutes_formatted_with_leading_zero(self):
        """Prüft, dass Minuten immer zweistellig formatiert werden."""
        applicant = self._make_applicant(
            min_hours=timedelta(hours=1, minutes=5),
            max_hours=timedelta(hours=2, minutes=30),
        )
        self.assertEqual(applicant.desired_hours_summary, "1:05–2:30 Std.")


# --- Employment property Tests ---


class EmploymentTests(TestCase):
    """Tests für die berechneten Properties von Employment."""

    def setUp(self):
        self.employee = Employee.objects.create(first_name="Max", last_name="Betreuer")
        self.salary_agreement = SalaryAgreement.objects.create(
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            salary_standard=Decimal("10.00"),
            salary_tandem=Decimal("15.00"),
            salary_coordination=Decimal("20.00"),
            salary_management=Decimal("25.00"),
            salary_honorary_standard=Decimal("5.00"),
            salary_honorary_tandem=Decimal("8.00"),
        )
        # SchoolDays für September 2024
        SchoolDays.objects.create(
            month=date(2024, 9, 1), school_days=20, public_holidays=1, vacation_days=0
        )

    def _make_employment(self, **kwargs):
        """Erstellt ein gespeichertes Employment mit sinnvollen Standardwerten."""
        defaults = dict(
            employee=self.employee,
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 30),
            weekly_hours=timedelta(hours=5),
            contract_type=Employment.ContractType.SCHOOL_ACCOMPANIMENT,
        )
        defaults.update(kwargs)
        return Employment.objects.create(**defaults)

    # --- daily_hours ---

    def test_daily_hours(self):
        """weekly_hours / 5 ergibt die täglichen Stunden."""
        emp = Employment(weekly_hours=timedelta(hours=5))
        self.assertEqual(emp.daily_hours, timedelta(hours=1))

    def test_daily_hours_with_minutes(self):
        """10:30 Wochenstunden geteilt durch 5 = 2:06 Tagesstunden."""
        emp = Employment(weekly_hours=timedelta(hours=10, minutes=30))
        self.assertEqual(emp.daily_hours, timedelta(hours=2, minutes=6))

    def test_daily_hours_none_when_no_weekly_hours(self):
        """Wenn weekly_hours None ist, soll daily_hours ebenfalls None sein."""
        emp = Employment(weekly_hours=None)
        self.assertIsNone(emp.daily_hours)

    # --- calculated_work_days ---

    def test_calculated_work_days(self):
        """Arbeitstage werden aus den SchoolDays-Stammdaten berechnet (20 für Sep 2024)."""
        emp = self._make_employment()
        self.assertEqual(emp.calculated_work_days, 20)

    def test_calculated_work_days_none_when_no_end_date(self):
        """Wenn end_date nicht gesetzt ist, soll calculated_work_days None sein."""
        emp = Employment(
            employee=self.employee,
            start_date=date(2024, 9, 1),
            end_date=None,
            weekly_hours=timedelta(hours=5),
        )
        self.assertIsNone(emp.calculated_work_days)

    # --- calculated_months ---

    def test_calculated_months_same_day_one_month_apart(self):
        """April 15 bis Mai 15 ergibt exakt 1.0 Monat."""
        emp = Employment(
            start_date=date(2024, 4, 15),
            end_date=date(2024, 5, 15),
        )
        self.assertEqual(emp.calculated_months, Decimal("1"))

    def test_calculated_months_full_year(self):
        """Januar 1 bis Dezember 31 ergibt exakt 12.0 Monate."""
        emp = Employment(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        self.assertEqual(emp.calculated_months, Decimal("12"))

    def test_calculated_months_with_day_fraction(self):
        """Sep 1 bis Sep 30: 29/30 ≈ 0.967 wird auf 1.0 gerundet."""
        emp = Employment(
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 30),
        )
        self.assertEqual(emp.calculated_months, Decimal("1.0"))

    def test_calculated_months_rounds_down_to_nearest_tenth(self):
        """Apr 1 bis Mai 2: 1 + 1/30 ≈ 1.033 wird auf 1.0 abgerundet."""
        emp = Employment(
            start_date=date(2024, 4, 1),
            end_date=date(2024, 5, 2),
        )
        self.assertEqual(emp.calculated_months, Decimal("1.0"))

    def test_calculated_months_rounds_up_to_nearest_tenth(self):
        """Apr 1 bis Mai 6: 1 + 5/30 ≈ 1.167 wird auf 1.2 aufgerundet."""
        emp = Employment(
            start_date=date(2024, 4, 1),
            end_date=date(2024, 5, 6),
        )
        self.assertEqual(emp.calculated_months, Decimal("1.2"))

    def test_calculated_months_none_when_no_end_date(self):
        """Wenn end_date nicht gesetzt ist, soll calculated_months None sein."""
        emp = Employment(start_date=date(2024, 9, 1), end_date=None)
        self.assertIsNone(emp.calculated_months)

    def test_calculated_months_uses_actual_month_days(self):
        """Aug 14 → Jan 31: 5 + 17/31(Jan) ≈ 5.548 → 5.5, nicht 5.6 wie mit /30."""
        emp = Employment(
            start_date=date(2025, 8, 14),
            end_date=date(2026, 1, 31),
        )
        self.assertEqual(emp.calculated_months, Decimal("5.5"))

    def test_calculated_months_borrows_when_end_day_earlier_than_start_day(self):
        """Aug 14 → Jan 5: borgt einen Monat, 4 + 22/31(Dez) ≈ 4.710 → 4.7."""
        emp = Employment(
            start_date=date(2025, 8, 14),
            end_date=date(2026, 1, 5),
        )
        self.assertEqual(emp.calculated_months, Decimal("4.7"))

    # --- yearly_hours ---

    def test_yearly_hours(self):
        """Jahresstunden = Tagesstunden × rechnerische Arbeitstage aus Stammdaten."""
        emp = self._make_employment()
        # daily_hours = 1h, calculated_work_days = 20 → 20h
        self.assertEqual(emp.yearly_hours, timedelta(hours=20))

    def test_yearly_hours_with_work_days_override(self):
        """Mit work_days_override werden die überschriebenen Tage verwendet."""
        emp = self._make_employment(work_days_override=10)
        # daily_hours = 1h, override = 10 → 10h
        self.assertEqual(emp.yearly_hours, timedelta(hours=10))

    def test_yearly_hours_none_when_no_end_date(self):
        """Ohne end_date können keine Jahresstunden berechnet werden."""
        emp = Employment(
            weekly_hours=timedelta(hours=5),
            start_date=date(2024, 9, 1),
            end_date=None,
        )
        self.assertIsNone(emp.yearly_hours)

    # --- monthly_hours ---

    def test_monthly_hours(self):
        """Monatsstunden = Jahresstunden / Vertragsmonate."""
        emp = self._make_employment(work_days_override=20, month_override=Decimal("2"))
        # yearly = 1h × 20 = 20h, months = 2 → monthly = 10h
        self.assertEqual(emp.monthly_hours, Decimal("10"))

    def test_monthly_hours_with_month_override(self):
        """month_override überschreibt die rechnerischen Vertragsmonate."""
        emp = self._make_employment(work_days_override=20, month_override=Decimal("4"))
        # yearly = 20h, months = 4 → monthly = 5h
        self.assertEqual(emp.monthly_hours, Decimal("5"))

    def test_monthly_hours_none_when_no_end_date(self):
        """Ohne end_date können keine Monatsstunden berechnet werden."""
        emp = Employment(
            weekly_hours=timedelta(hours=5),
            start_date=date(2024, 9, 1),
            end_date=None,
        )
        self.assertIsNone(emp.monthly_hours)

    # --- salary_agreement ---

    def test_salary_agreement_found_by_start_date(self):
        """Gehaltsvereinbarung wird über das Startdatum gefunden."""
        emp = self._make_employment(start_date=date(2024, 6, 1))
        self.assertEqual(emp.salary_agreement, self.salary_agreement)

    def test_salary_agreement_not_found_outside_dates(self):
        """Keine Gehaltsvereinbarung wenn start_date außerhalb der Gültigkeit liegt."""
        emp = self._make_employment(
            start_date=date(2025, 1, 1), end_date=date(2025, 6, 30)
        )
        self.assertIsNone(emp.salary_agreement)

    # --- calculated_gross_salary ---

    def test_gross_salary_school_accompaniment(self):
        """Schulbegleitung verwendet salary_standard für die Berechnung."""
        emp = self._make_employment(
            work_days_override=20,
            month_override=Decimal("1"),
            contract_type=Employment.ContractType.SCHOOL_ACCOMPANIMENT,
        )
        # monthly_hours = 20h, rate = 10.00 → 200 → gerundet auf 10 = 200
        self.assertEqual(emp.calculated_gross_salary, Decimal("200"))

    def test_gross_salary_tandem(self):
        """Tandem verwendet salary_tandem für die Berechnung."""
        emp = self._make_employment(
            work_days_override=20,
            month_override=Decimal("1"),
            contract_type=Employment.ContractType.TANDEM,
        )
        # monthly_hours = 20h, rate = 15.00 → 300 → gerundet auf 10 = 300
        self.assertEqual(emp.calculated_gross_salary, Decimal("300"))

    def test_gross_salary_rounds_half_up(self):
        """195 € wird auf 200 € aufgerundet (ROUND_HALF_UP)."""
        # daily = 1.5h (weekly=7.5h), work_days=13, months=1 → monthly=19.5h
        # rate=10 → 195.0 → rounds to 200
        emp = self._make_employment(
            weekly_hours=timedelta(hours=7, minutes=30),
            work_days_override=13,
            month_override=Decimal("1"),
            contract_type=Employment.ContractType.SCHOOL_ACCOMPANIMENT,
        )
        self.assertEqual(emp.calculated_gross_salary, Decimal("200"))

    def test_gross_salary_rounds_down(self):
        """182 € wird auf 180 € abgerundet (Einer < 5)."""
        # daily = 1h24m (weekly=7h), work_days=13, months=1 → monthly=18.2h
        # rate=10 → 182.0 → rounds to 180
        emp = self._make_employment(
            weekly_hours=timedelta(hours=7),
            work_days_override=13,
            month_override=Decimal("1"),
            contract_type=Employment.ContractType.SCHOOL_ACCOMPANIMENT,
        )
        self.assertEqual(emp.calculated_gross_salary, Decimal("180"))

    def test_gross_salary_override_does_not_affect_calculated(self):
        """gross_salary_override hat keinen Einfluss auf calculated_gross_salary."""
        emp = self._make_employment(
            work_days_override=20,
            month_override=Decimal("1"),
            gross_salary_override=Decimal("999.00"),
        )
        # Rechnerisch: 20h * 10€/h = 200€ — unabhängig vom Override
        self.assertEqual(emp.calculated_gross_salary, Decimal("200"))

    def test_gross_salary_none_when_no_salary_agreement(self):
        """Kein Brutto wenn keine Gehaltsvereinbarung für das Startdatum vorhanden."""
        emp = self._make_employment(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),
            work_days_override=20,
            month_override=Decimal("1"),
        )
        self.assertIsNone(emp.calculated_gross_salary)

    def test_gross_salary_none_when_no_contract_type(self):
        """Kein Brutto wenn kein Vertragstyp gesetzt ist."""
        emp = self._make_employment(
            work_days_override=20,
            month_override=Decimal("1"),
            contract_type="",
        )
        self.assertIsNone(emp.calculated_gross_salary)

    def test_gross_salary_none_when_no_end_date(self):
        """Kein Brutto wenn kein end_date gesetzt ist (keine Monatsstunden berechenbar)."""
        emp = self._make_employment(end_date=None)
        self.assertIsNone(emp.calculated_gross_salary)

    # --- yearly_gross_salary ---

    def test_yearly_gross_salary(self):
        """Jahresbrutto = monatliches Brutto × Vertragsmonate."""
        emp = self._make_employment(
            work_days_override=20,
            month_override=Decimal("2"),
            contract_type=Employment.ContractType.SCHOOL_ACCOMPANIMENT,
        )
        # monthly_hours = 20h / 2 = 10h, rate=10 → gross=100, yearly=100*2=200
        self.assertEqual(emp.yearly_gross_salary, Decimal("200"))

    def test_yearly_gross_salary_none_when_no_gross(self):
        """Kein Jahresbrutto wenn calculated_gross_salary nicht berechnet werden kann."""
        emp = self._make_employment(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),
            work_days_override=20,
            month_override=Decimal("1"),
        )
        self.assertIsNone(emp.yearly_gross_salary)
