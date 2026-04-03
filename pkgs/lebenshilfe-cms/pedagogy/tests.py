from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase

from base.models import SchoolDays
from finance.models import CostPayer, FeeAgreement
from hr.models import Employee
from pedagogy.models import School, Student, Supervision


class SupervisionTests(TestCase):
    """Tests für die berechneten Properties und die save()-Logik von Supervision."""

    def setUp(self):
        self.payer = CostPayer.objects.create(identifier="Bezirk Testland")
        self.school = School.objects.create(name="Testschule")
        self.caretaker = Employee.objects.create(
            first_name="Klaus", last_name="Betreuer"
        )
        self.student = Student.objects.create(
            first_name="Anna", last_name="Schüler", payer=self.payer
        )
        self.tandem_student = Student.objects.create(
            first_name="Ben", last_name="Tandem", payer=self.payer
        )
        self.fee_agreement = FeeAgreement.objects.create(
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            price_standard=Decimal("10.00"),
            price_tandem=Decimal("15.00"),
            price_coordination=Decimal("20.00"),
            responsible_payer=self.payer,
        )
        # SchoolDays für September 2024
        SchoolDays.objects.create(
            month=date(2024, 9, 1), school_days=20, public_holidays=1, vacation_days=0
        )

    def _make_supervision(self, **kwargs):
        """Erstellt eine gespeicherte Supervision mit sinnvollen Standardwerten."""
        defaults = dict(
            student=self.student,
            caretaker=self.caretaker,
            school=self.school,
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 30),
            weekly_hours=timedelta(hours=5),
        )
        defaults.update(kwargs)
        return Supervision.objects.create(**defaults)

    # --- daily_hours ---

    def test_daily_hours(self):
        """weekly_hours / 5 ergibt die täglichen Stunden."""
        sup = Supervision(weekly_hours=timedelta(hours=5))
        self.assertEqual(sup.daily_hours, timedelta(hours=1))

    def test_daily_hours_with_minutes(self):
        """10:30 Wochenstunden geteilt durch 5 = 2:06 Tagesstunden."""
        sup = Supervision(weekly_hours=timedelta(hours=10, minutes=30))
        self.assertEqual(sup.daily_hours, timedelta(hours=2, minutes=6))

    def test_daily_hours_none_when_no_weekly_hours(self):
        """Wenn weekly_hours None ist, soll daily_hours ebenfalls None sein."""
        sup = Supervision(weekly_hours=None)
        self.assertIsNone(sup.daily_hours)

    # --- total_hours ---

    def test_total_hours_with_override(self):
        """Mit school_days_override werden die angegebenen Tage verwendet."""
        sup = Supervision(weekly_hours=timedelta(hours=5), school_days_override=10)
        # daily_hours = 1h, override = 10 → total = 10h
        self.assertEqual(sup.total_hours, timedelta(hours=10))

    def test_total_hours_without_override_uses_school_days(self):
        """Ohne Override werden die Schultage aus der DB berechnet (20 Tage für Sep 2024)."""
        sup = self._make_supervision(school_days_override=None)
        # daily_hours = 1h, school_days = 20 → total = 20h
        self.assertEqual(sup.total_hours, timedelta(hours=20))

    def test_total_hours_none_when_no_weekly_hours(self):
        """Wenn weekly_hours None ist, soll total_hours ebenfalls None sein."""
        sup = Supervision(weekly_hours=None, school_days_override=10)
        self.assertIsNone(sup.total_hours)

    # --- fee_agreement ---

    def test_fee_agreement_found_by_responsible_payer(self):
        """Entgeltvereinbarung wird über den Kostenträger und das Startdatum gefunden."""
        sup = self._make_supervision(start_date=date(2024, 9, 1))
        self.assertEqual(sup.fee_agreement, self.fee_agreement)

    def test_fee_agreement_not_found_outside_dates(self):
        """Keine Entgeltvereinbarung wenn start_date außerhalb der Gültigkeit liegt."""
        sup = self._make_supervision(
            start_date=date(2025, 1, 1), end_date=date(2025, 6, 30)
        )
        self.assertIsNone(sup.fee_agreement)

    def test_fee_agreement_not_found_for_other_payer(self):
        """Keine Entgeltvereinbarung wenn kein passender Kostenträger vorhanden ist."""
        other_payer = CostPayer.objects.create(identifier="Anderer Kostenträger")
        other_student = Student.objects.create(
            first_name="Lena", last_name="Andere", payer=other_payer
        )
        sup = self._make_supervision(student=other_student, start_date=date(2024, 9, 1))
        self.assertIsNone(sup.fee_agreement)

    # --- total_amount ---

    def test_total_amount_standard(self):
        """Ohne Tandem wird price_standard verwendet."""
        sup = self._make_supervision(school_days_override=10)
        # daily_hours = 1h, override = 10 → total = 10h → 10.00 * 10 = 100.00
        self.assertEqual(sup.total_amount, Decimal("100.00"))

    def test_total_amount_tandem(self):
        """Mit Tandem wird price_tandem verwendet."""
        sup = self._make_supervision(
            tandem=self.tandem_student,
            school_days_override=10,
        )
        # daily_hours = 1h, override = 10 → total = 10h → 15.00 * 10 = 150.00
        self.assertEqual(sup.total_amount, Decimal("150.00"))

    def test_total_amount_none_when_no_fee_agreement(self):
        """Kein Betrag wenn keine Entgeltvereinbarung gefunden wird."""
        sup = self._make_supervision(
            start_date=date(2025, 1, 1), end_date=date(2025, 6, 30)
        )
        self.assertIsNone(sup.total_amount)

    # --- monthly_installment ---

    def test_monthly_installment_single_month(self):
        """Gesamtbetrag bei einem einzigen Monat ergibt den vollen Betrag als Abschlag."""
        sup = self._make_supervision(
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 30),
            school_days_override=10,
        )
        # total = 100.00, months = 1 → installment = 100.00
        self.assertEqual(sup.monthly_installment, Decimal("100.00"))

    def test_monthly_installment_multi_month(self):
        """Gesamtbetrag wird durch die Anzahl der Monate geteilt."""
        SchoolDays.objects.create(
            month=date(2024, 10, 1), school_days=22, public_holidays=0, vacation_days=0
        )
        SchoolDays.objects.create(
            month=date(2024, 11, 1), school_days=18, public_holidays=0, vacation_days=0
        )
        sup = self._make_supervision(
            start_date=date(2024, 9, 1),
            end_date=date(2024, 11, 30),
            school_days_override=30,
        )
        # total_hours = 1h * 30 = 30h → total_amount = 10.00 * 30 = 300.00
        # months = (2024-2024)*12 + 11 - 9 + 1 = 3
        # installment = 300.00 / 3 = 100.00
        self.assertEqual(sup.monthly_installment, Decimal("100.00"))

    def test_monthly_installment_none_when_no_fee_agreement(self):
        """Kein Abschlag wenn kein Gesamtbetrag berechnet werden kann."""
        sup = self._make_supervision(
            start_date=date(2025, 1, 1), end_date=date(2025, 6, 30)
        )
        self.assertIsNone(sup.monthly_installment)

    # --- save() ---

    def test_save_mirrors_prophylactic_when_no_tandem(self):
        """is_tandem_prophylactic spiegelt is_prophylactic, wenn kein Tandem gesetzt ist."""
        sup = self._make_supervision(
            tandem=None, is_prophylactic=False, is_tandem_prophylactic=True
        )
        sup.refresh_from_db()
        self.assertFalse(sup.is_tandem_prophylactic)

    def test_save_keeps_tandem_prophylactic_when_tandem_set(self):
        """is_tandem_prophylactic bleibt erhalten, wenn ein Tandem gesetzt ist."""
        sup = self._make_supervision(
            tandem=self.tandem_student,
            is_tandem_prophylactic=True,
        )
        sup.refresh_from_db()
        self.assertTrue(sup.is_tandem_prophylactic)

    def test_save_mirrors_prophylactic_on_tandem_removal(self):
        """is_tandem_prophylactic spiegelt is_prophylactic, wenn das Tandem nachträglich entfernt wird."""
        sup = self._make_supervision(
            tandem=self.tandem_student,
            is_prophylactic=False,
            is_tandem_prophylactic=True,
        )
        sup.tandem = None
        sup.save()
        sup.refresh_from_db()
        self.assertFalse(sup.is_tandem_prophylactic)
