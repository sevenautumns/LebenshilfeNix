from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from base.models import SchoolDays
from finance.models import CostPayer, FeeAgreement, PoolAgreement
from hr.models import Employee
from pedagogy.calculators import SupervisionCalculatorInput, run_supervision_calculation
from pedagogy.models import School, Student, Supervision


class SupervisionModelTests(TestCase):
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
        SchoolDays.objects.create(
            month=date(2024, 9, 1), school_days=20, public_holidays=1, vacation_days=0
        )

    def _make_supervision(self, **kwargs):
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

    # --- fee_agreement ---

    def test_fee_agreement_found_by_responsible_payer(self):
        """Entgeltvereinbarung wird über den Kostenträger und das Startdatum gefunden."""
        fee = FeeAgreement.objects.create(
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            price_standard=Decimal("10.00"),
            price_tandem=Decimal("15.00"),
            price_coordination=Decimal("20.00"),
            responsible_payer=self.payer,
        )
        sup = self._make_supervision(start_date=date(2024, 9, 1))
        self.assertEqual(sup.fee_agreement, fee)

    def test_fee_agreement_not_found_outside_dates(self):
        """Keine Entgeltvereinbarung wenn start_date außerhalb der Gültigkeit liegt."""
        FeeAgreement.objects.create(
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            price_standard=Decimal("10.00"),
            price_tandem=Decimal("15.00"),
            price_coordination=Decimal("20.00"),
            responsible_payer=self.payer,
        )
        sup = self._make_supervision(
            start_date=date(2025, 1, 1), end_date=date(2025, 6, 30)
        )
        self.assertIsNone(sup.fee_agreement)

    def test_fee_agreement_not_found_for_other_payer(self):
        """Keine Entgeltvereinbarung wenn kein passender Kostenträger vorhanden ist."""
        FeeAgreement.objects.create(
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            price_standard=Decimal("10.00"),
            price_tandem=Decimal("15.00"),
            price_coordination=Decimal("20.00"),
            responsible_payer=self.payer,
        )
        other_payer = CostPayer.objects.create(identifier="Anderer Kostenträger")
        other_student = Student.objects.create(
            first_name="Lena", last_name="Andere", payer=other_payer
        )
        sup = self._make_supervision(student=other_student, start_date=date(2024, 9, 1))
        self.assertIsNone(sup.fee_agreement)

    # --- calculated_months ---

    def test_calculated_months(self):
        """Berechnete Monate hängen von den Kalendermonaten ab."""
        sup = self._make_supervision(
            start_date=date(2024, 9, 15),
            end_date=date(2024, 11, 5),
        )
        self.assertEqual(sup.calculated_months, 3)

    # --- save() ---

    def test_save_resets_tandem_prophylactic_when_no_tandem(self):
        """is_tandem_prophylactic wird auf False gesetzt, wenn kein Tandem gesetzt ist."""
        sup = self._make_supervision(tandem=None, is_tandem_prophylactic=True)
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

    def test_save_resets_tandem_prophylactic_on_tandem_removal(self):
        """is_tandem_prophylactic wird auf False gesetzt, wenn das Tandem entfernt wird."""
        sup = self._make_supervision(
            tandem=self.tandem_student,
            is_tandem_prophylactic=True,
        )
        sup.tandem = None
        sup.save()
        sup.refresh_from_db()
        self.assertFalse(sup.is_tandem_prophylactic)


class SupervisionCalculatorTests(TestCase):
    """Tests für run_supervision_calculation() in pedagogy/calculators.py."""

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
        SchoolDays.objects.create(
            month=date(2024, 9, 1), school_days=20, public_holidays=1, vacation_days=0
        )

    def _make_supervision(self, **kwargs):
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

    def _calc(self, supervision, **kwargs):
        return run_supervision_calculation(
            SupervisionCalculatorInput(supervision=supervision, **kwargs)
        )

    # --- FEV-Pfad ---

    def test_fev_total_amount_standard(self):
        """Ohne Tandem wird price_standard für den Gesamtbetrag verwendet."""
        sup = self._make_supervision()
        result = self._calc(sup, school_days_override=10)
        # daily_hours = 1h, 10 days → yearly = 10h → 10.00 * 10 = 100.00
        self.assertEqual(result.calculated_total_amount, Decimal("100.00"))
        self.assertFalse(result.is_pool_rate)

    def test_fev_total_amount_tandem(self):
        """Mit Tandem wird price_tandem verwendet."""
        sup = self._make_supervision(tandem=self.tandem_student)
        result = self._calc(sup, school_days_override=10)
        # 15.00 * 10 = 150.00
        self.assertEqual(result.calculated_total_amount, Decimal("150.00"))

    def test_fev_monthly_installment_single_month(self):
        """Gesamtbetrag / 1 Monat = voller Betrag als Abschlag."""
        sup = self._make_supervision()
        result = self._calc(sup, school_days_override=10)
        self.assertEqual(result.calculated_monthly_installment, Decimal("100.00"))

    def test_fev_monthly_installment_multi_month(self):
        """Gesamtbetrag wird durch die Anzahl der Monate geteilt."""
        sup = self._make_supervision(
            start_date=date(2024, 9, 1),
            end_date=date(2024, 11, 30),
        )
        result = self._calc(sup, school_days_override=30)
        # total = 10.00 * 30h = 300.00, months = 3 → installment = 100.00
        self.assertEqual(result.calculated_total_amount, Decimal("300.00"))
        self.assertEqual(result.calculated_monthly_installment, Decimal("100.00"))
        self.assertEqual(result.months, Decimal("3"))

    def test_fev_months_override_respected(self):
        """months_override überschreibt die berechneten Monate."""
        sup = self._make_supervision(
            start_date=date(2024, 9, 1),
            end_date=date(2024, 11, 30),
        )
        result = self._calc(sup, school_days_override=30, months_override=Decimal("2"))
        # total = 300.00, override = 2 → installment = 150.00
        self.assertEqual(result.calculated_monthly_installment, Decimal("150.00"))
        self.assertEqual(result.months, Decimal("2"))

    def test_fev_school_days_override_respected(self):
        """school_days_override überschreibt die berechneten Schultage."""
        sup = self._make_supervision()
        result = self._calc(sup, school_days_override=5)
        # daily_hours = 1h, 5 days → yearly = 5h → 10.00 * 5 = 50.00
        self.assertEqual(result.calculated_total_amount, Decimal("50.00"))
        self.assertEqual(result.school_days, 5)

    def test_fev_fee_agreement_override_used(self):
        """fee_agreement_override überschreibt die automatisch gefundene FEV."""
        other_fee = FeeAgreement.objects.create(
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            price_standard=Decimal("20.00"),
            price_tandem=Decimal("25.00"),
            price_coordination=Decimal("30.00"),
            responsible_payer=CostPayer.objects.create(identifier="Anderer"),
        )
        sup = self._make_supervision()
        result = self._calc(
            sup, school_days_override=10, fee_agreement_override=other_fee
        )
        # 20.00 * 10 = 200.00
        self.assertEqual(result.calculated_total_amount, Decimal("200.00"))
        self.assertEqual(result.fee_agreement, other_fee)

    def test_fev_none_when_no_fee_agreement(self):
        """Kein Betrag wenn keine Entgeltvereinbarung vorhanden ist."""
        sup = self._make_supervision(
            start_date=date(2025, 1, 1), end_date=date(2025, 6, 30)
        )
        result = self._calc(sup)
        self.assertIsNone(result.calculated_total_amount)
        self.assertIsNone(result.calculated_monthly_installment)
        self.assertTrue(len(result.warnings) > 0)

    def test_fev_none_when_no_weekly_hours(self):
        """Kein Betrag wenn keine Wochenstunden angegeben sind."""
        sup = Supervision(
            student=self.student,
            caretaker=self.caretaker,
            school=self.school,
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 30),
            weekly_hours=None,
        )
        result = self._calc(sup, school_days_override=10)
        self.assertIsNone(result.calculated_total_amount)

    # --- Pool-Pfad ---

    def test_pool_uses_flat_rate_as_installment(self):
        """Bei Poolvereinbarung wird flat_rate als Abschlag verwendet."""
        pool = PoolAgreement.objects.create(
            payer=self.payer,
            school=self.school,
            flat_rate=Decimal("500.00"),
            approved_supervisions=5,
            prophylactic_supervisions=2,
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
        )
        sup = self._make_supervision()
        result = self._calc(sup)
        self.assertTrue(result.is_pool_rate)
        self.assertEqual(result.pool_agreement, pool)
        self.assertEqual(result.calculated_monthly_installment, Decimal("500.00"))

    def test_pool_total_amount_is_flat_rate_times_months(self):
        """Gesamtbetrag bei Pool = flat_rate × Monate."""
        PoolAgreement.objects.create(
            payer=self.payer,
            school=self.school,
            flat_rate=Decimal("500.00"),
            approved_supervisions=5,
            prophylactic_supervisions=2,
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
        )
        sup = self._make_supervision(
            start_date=date(2024, 9, 1), end_date=date(2024, 11, 30)
        )
        result = self._calc(sup)
        # months = 3, flat_rate = 500 → total = 1500
        self.assertEqual(result.calculated_total_amount, Decimal("1500.00"))

    def test_pool_months_override_affects_total(self):
        """months_override beeinflusst den Gesamtbetrag auch beim Pool-Pfad."""
        PoolAgreement.objects.create(
            payer=self.payer,
            school=self.school,
            flat_rate=Decimal("500.00"),
            approved_supervisions=5,
            prophylactic_supervisions=2,
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
        )
        sup = self._make_supervision(
            start_date=date(2024, 9, 1), end_date=date(2024, 11, 30)
        )
        result = self._calc(sup, months_override=Decimal("2"))
        self.assertEqual(result.calculated_total_amount, Decimal("1000.00"))
        self.assertEqual(result.calculated_monthly_installment, Decimal("500.00"))

    def test_pool_not_applied_when_outside_validity(self):
        """Poolvereinbarung wird nicht verwendet wenn start_date außerhalb liegt."""
        PoolAgreement.objects.create(
            payer=self.payer,
            school=self.school,
            flat_rate=Decimal("500.00"),
            approved_supervisions=5,
            prophylactic_supervisions=2,
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 8, 31),
        )
        sup = self._make_supervision(start_date=date(2024, 9, 1))
        result = self._calc(sup)
        self.assertFalse(result.is_pool_rate)

    def test_pool_not_applied_for_other_school(self):
        """Poolvereinbarung gilt nicht für eine andere Schule."""
        other_school = School.objects.create(name="Andere Schule")
        PoolAgreement.objects.create(
            payer=self.payer,
            school=other_school,
            flat_rate=Decimal("500.00"),
            approved_supervisions=5,
            prophylactic_supervisions=2,
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
        )
        sup = self._make_supervision()
        result = self._calc(sup)
        self.assertFalse(result.is_pool_rate)
