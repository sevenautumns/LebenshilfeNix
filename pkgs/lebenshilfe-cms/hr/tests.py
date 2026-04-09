from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from finance.models import SalaryAgreement
from hr.calculators import (
    CalculatorInput,
    calculate_months,
    run_calculation,
)
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


# --- hr.calculators Tests ---


class CalculatorTests(TestCase):
    """Tests für hr.calculators — ersetzt die ehemaligen Employment-Property-Tests."""

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

    def _make_input(self, **kwargs) -> CalculatorInput:
        """Erstellt ein CalculatorInput mit sinnvollen Standardwerten."""
        defaults = dict(
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 30),
            weekly_hours=timedelta(hours=5),
            contract_type=Employment.ContractType.SCHOOL_ACCOMPANIMENT,
        )
        defaults.update(kwargs)
        return CalculatorInput(**defaults)

    # --- calculate_months ---

    def test_calculated_months_same_day_one_month_apart(self):
        """April 15 bis Mai 15 ergibt exakt 1.0 Monat."""
        self.assertEqual(
            calculate_months(date(2024, 4, 15), date(2024, 5, 15)), Decimal("1")
        )

    def test_calculated_months_full_year(self):
        """Januar 1 bis Dezember 31 ergibt exakt 12.0 Monate."""
        self.assertEqual(
            calculate_months(date(2024, 1, 1), date(2024, 12, 31)), Decimal("12")
        )

    def test_calculated_months_with_day_fraction(self):
        """Sep 1 bis Sep 30: 29/30 ≈ 0.967 wird auf 1.0 gerundet."""
        self.assertEqual(
            calculate_months(date(2024, 9, 1), date(2024, 9, 30)), Decimal("1.0")
        )

    def test_calculated_months_rounds_down_to_nearest_half_month(self):
        """Apr 1 bis Mai 2: 1 + 1/30 ≈ 1.033 wird auf 1.0 abgerundet."""
        self.assertEqual(
            calculate_months(date(2024, 4, 1), date(2024, 5, 2)), Decimal("1.0")
        )

    def test_calculated_months_rounds_up_to_nearest_half_month(self):
        """Apr 1 bis Mai 9: 1 + 8/30 ≈ 1.266 wird auf 1.5 aufgerundet."""
        self.assertEqual(
            calculate_months(date(2024, 4, 1), date(2024, 5, 9)), Decimal("1.5")
        )

    def test_calculated_months_none_when_no_end_date(self):
        """Wenn end_date nicht gesetzt ist, soll calculated_months None sein."""
        result = run_calculation(self._make_input(end_date=None))
        self.assertIsNone(result.calculated_months)

    def test_calculated_months_uses_actual_month_days(self):
        """Aug 14 → Jan 31: 5 + 17/31(Jan) ≈ 5.548 → 5.5, nicht 5.6 wie mit /30."""
        self.assertEqual(
            calculate_months(date(2025, 8, 14), date(2026, 1, 31)), Decimal("5.5")
        )

    def test_calculated_months_borrows_when_end_day_earlier_than_start_day(self):
        """Aug 14 → Jan 5: borgt einen Monat, 4 + 22/31(Dez) ≈ 4.710 → 4.5."""
        self.assertEqual(
            calculate_months(date(2025, 8, 14), date(2026, 1, 5)), Decimal("4.5")
        )

    # --- salary_agreement via run_calculation ---

    def test_salary_agreement_found_by_start_date(self):
        """Gehaltsvereinbarung wird über das Startdatum gefunden."""
        result = run_calculation(
            self._make_input(start_date=date(2024, 6, 1), end_date=date(2024, 6, 30))
        )
        self.assertEqual(result.salary_agreement, self.salary_agreement)

    def test_salary_agreement_not_found_outside_dates(self):
        """Keine Gehaltsvereinbarung wenn start_date außerhalb der Gültigkeit liegt."""
        result = run_calculation(
            self._make_input(start_date=date(2025, 1, 1), end_date=date(2025, 6, 30))
        )
        self.assertIsNone(result.salary_agreement)

    # --- monthly_gross_salary via run_calculation ---

    def test_gross_salary_school_accompaniment(self):
        """Schulbegleitung verwendet salary_standard für die Berechnung."""
        # weekly_hours = 5h, rate = 10.00 -> 5 * 4 * 10 = 200
        result = run_calculation(
            self._make_input(
                weekly_hours=timedelta(hours=5),
                contract_type=Employment.ContractType.SCHOOL_ACCOMPANIMENT,
            )
        )
        self.assertEqual(result.monthly_gross_salary, Decimal("200"))

    def test_gross_salary_tandem(self):
        """Tandem verwendet salary_tandem für die Berechnung."""
        # weekly_hours = 5h, rate = 15.00 -> 5 * 4 * 15 = 300
        result = run_calculation(
            self._make_input(
                weekly_hours=timedelta(hours=5),
                contract_type=Employment.ContractType.TANDEM,
            )
        )
        self.assertEqual(result.monthly_gross_salary, Decimal("300"))

    def test_gross_salary_rounds_half_up(self):
        """195 € wird auf 200 € aufgerundet (ROUND_HALF_UP)."""
        # weekly_hours = 4.875h (4h 52m 30s), rate=10 -> 4.875 * 4 * 10 = 195.0 -> rounds to 200
        result = run_calculation(
            self._make_input(
                weekly_hours=timedelta(hours=4, minutes=52, seconds=30),
                contract_type=Employment.ContractType.SCHOOL_ACCOMPANIMENT,
            )
        )
        self.assertEqual(result.monthly_gross_salary, Decimal("200"))

    def test_gross_salary_rounds_down(self):
        """182 € wird auf 180 € abgerundet (Einer < 5)."""
        # weekly_hours = 4.55h (4h 33m), rate=10 -> 4.55 * 4 * 10 = 182.0 -> rounds to 180
        result = run_calculation(
            self._make_input(
                weekly_hours=timedelta(hours=4, minutes=33),
                contract_type=Employment.ContractType.SCHOOL_ACCOMPANIMENT,
            )
        )
        self.assertEqual(result.monthly_gross_salary, Decimal("180"))

    def test_gross_salary_none_when_no_salary_agreement(self):
        """Kein Brutto wenn keine Gehaltsvereinbarung für das Startdatum vorhanden."""
        result = run_calculation(
            self._make_input(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 6, 30),
            )
        )
        self.assertIsNone(result.monthly_gross_salary)

    def test_gross_salary_none_when_no_contract_type(self):
        """Kein Brutto wenn kein Vertragstyp gesetzt ist."""
        result = run_calculation(self._make_input(contract_type=""))
        self.assertIsNone(result.monthly_gross_salary)

    # --- yearly_gross_salary via run_calculation ---

    def test_yearly_gross_salary(self):
        """Jahresbrutto = monatliches Brutto × Vertragsmonate."""
        # weekly_hours = 2.5h, rate=10 -> gross=100, yearly=100*2=200
        result = run_calculation(
            self._make_input(
                weekly_hours=timedelta(hours=2, minutes=30),
                contract_type=Employment.ContractType.SCHOOL_ACCOMPANIMENT,
                months_override=Decimal("2"),
            )
        )
        self.assertEqual(result.yearly_gross_salary, Decimal("200"))

    def test_yearly_gross_salary_none_when_no_gross(self):
        """Kein Jahresbrutto wenn monthly_gross_salary nicht berechnet werden kann."""
        result = run_calculation(
            self._make_input(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 6, 30),
            )
        )
        self.assertIsNone(result.yearly_gross_salary)


# --- Calculator View Smoke Tests ---


class CalculatorViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.client = Client()
        self.client.login(username="admin", password="password")

        self.employee = Employee.objects.create(first_name="Anna", last_name="Test")
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
        self.employment = Employment.objects.create(
            employee=self.employee,
            start_date=date(2024, 9, 1),
            end_date=date(2024, 12, 31),
            weekly_hours=timedelta(hours=5),
            contract_type=Employment.ContractType.SCHOOL_ACCOMPANIMENT,
        )

    def test_calculator_page_get(self):
        """GET auf die Calculator-Seite liefert HTTP 200."""
        url = reverse("admin:hr_employment_calculator", args=[self.employment.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_calculator_404_for_missing_employment(self):
        """GET mit nicht existierender pk liefert HTTP 404."""
        url = reverse("admin:hr_employment_calculator", args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_calculator_post_months_override(self):
        """POST mit months_override liefert HTTP 200 und verarbeitet den Wert."""
        url = reverse("admin:hr_employment_calculator", args=[self.employment.pk])
        response = self.client.post(url, {"months_override": "3.0"})
        self.assertEqual(response.status_code, 200)

    def test_calculator_post_salary_agreement_override(self):
        """POST mit salary_agreement_override liefert HTTP 200 und nutzt das gewählte Agreement."""
        url = reverse("admin:hr_employment_calculator", args=[self.employment.pk])
        response = self.client.post(
            url, {"salary_agreement_override": str(self.salary_agreement.pk)}
        )
        self.assertEqual(response.status_code, 200)

    def test_apply_redirects_to_calculator(self):
        """POST auf /apply/ speichert das Brutto und leitet zurück zum Rechner."""
        url = reverse("admin:hr_employment_calculator_apply", args=[self.employment.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse("admin:hr_employment_calculator", args=[self.employment.pk]),
            response["Location"],
        )
