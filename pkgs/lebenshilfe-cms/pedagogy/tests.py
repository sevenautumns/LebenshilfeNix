from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from base.models import SchoolDays
from finance.models import CostPayer, FeeAgreement, PoolAgreement
from hr.models import Employee
from pedagogy.calculators import (
    SupervisionCalculatorInput,
    calculate_supervision_months,
    run_supervision_calculation,
)
from pedagogy.models import Request, School, Student, Supervision, TandemPairing


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
        """7-Tage-Regel: Endmonat mit <7 Tagen zählt nicht."""
        sup = self._make_supervision(
            start_date=date(2024, 9, 15),
            end_date=date(2024, 11, 5),
        )
        # Sep: 16 Tage verbleibend → zählt; Okt: Mittelmonat → zählt; Nov: 5 Tage → zählt nicht
        self.assertEqual(sup.calculated_months, 2)


class CalculateSupervisionMonthsTests(TestCase):
    """Tests für calculate_supervision_months() — 7-Tage-Regel."""

    def test_full_months_both_sides(self):
        """Start am 1., Ende am letzten: beide Monate zählen → 10."""
        self.assertEqual(
            calculate_supervision_months(date(2025, 9, 1), date(2026, 6, 30)), 10
        )

    def test_start_and_end_have_enough_days(self):
        """Start am 15., Ende am 15.: je 16 bzw. 15 Tage → beide zählen → 10."""
        self.assertEqual(
            calculate_supervision_months(date(2025, 9, 15), date(2026, 6, 15)), 10
        )

    def test_both_months_too_short(self):
        """Start am 25. Sep (6 Tage), Ende am 5. Jun (5 Tage): beide fallen raus → 8."""
        self.assertEqual(
            calculate_supervision_months(date(2025, 9, 25), date(2026, 6, 5)), 8
        )

    def test_only_end_month_counts(self):
        """Start am 25. Sep (6 Tage → nein), Ende am 10. Jun (10 Tage → ja) → 9."""
        self.assertEqual(
            calculate_supervision_months(date(2025, 9, 25), date(2026, 6, 10)), 9
        )

    def test_only_start_month_counts(self):
        """Start am 1. Sep (30 Tage → ja), Ende am 5. Jun (5 Tage → nein) → 9."""
        self.assertEqual(
            calculate_supervision_months(date(2025, 9, 1), date(2026, 6, 5)), 9
        )

    def test_same_month(self):
        """Start und Ende im selben Monat → immer 1."""
        self.assertEqual(
            calculate_supervision_months(date(2025, 9, 1), date(2025, 9, 30)), 1
        )
        self.assertEqual(
            calculate_supervision_months(date(2025, 9, 25), date(2025, 9, 27)), 1
        )

    def test_minimum_one_month(self):
        """Auch wenn beide Monate < 7 Tage: mindestens 1 Monat."""
        # Sep 26 → Okt 1: Sep=5 Tage, Okt=1 Tag, middle=0 → max(1, 0)=1
        self.assertEqual(
            calculate_supervision_months(date(2025, 9, 26), date(2025, 10, 1)), 1
        )


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
        """Mit TandemPairing wird price_tandem verwendet und Endbetrag halbiert."""
        sup = self._make_supervision()
        tandem_sup = self._make_supervision(student=self.tandem_student)
        TandemPairing.objects.create(supervision_a=sup, supervision_b=tandem_sup)
        result = self._calc(sup, school_days_override=10)
        # 15.00 * 10 * 0.5 = 75.00
        self.assertEqual(result.calculated_total_amount, Decimal("75.00"))
        self.assertTrue(result.is_tandem)

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

    def test_fev_override_ignores_pool(self):
        """fee_agreement_override überstimmt einen vorhandenen Pool ohne use_fee_agreement."""
        PoolAgreement.objects.create(
            payer=self.payer,
            school=self.school,
            flat_rate=Decimal("500.00"),
            approved_supervisions=5,
            prophylactic_supervisions=2,
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
        )
        other_fee = FeeAgreement.objects.create(
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            price_standard=Decimal("20.00"),
            price_tandem=Decimal("25.00"),
            price_coordination=Decimal("30.00"),
            responsible_payer=CostPayer.objects.create(identifier="Anderer2"),
        )
        sup = self._make_supervision()
        result = self._calc(
            sup, school_days_override=10, fee_agreement_override=other_fee
        )
        self.assertFalse(result.is_pool_rate)
        self.assertEqual(result.fee_agreement, other_fee)
        # 20.00 * 10 = 200.00 (Pool ignoriert)
        self.assertEqual(result.calculated_total_amount, Decimal("200.00"))

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


class SupervisionCalculatorViewTests(TestCase):
    """Smoke-Tests für die SupervisionCalculatorView in pedagogy/admin.py."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.test import Client

        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.client = Client()
        self.client.login(username="admin", password="password")

        self.payer = CostPayer.objects.create(identifier="Bezirk Testland")
        self.school = School.objects.create(name="Testschule")
        self.caretaker = Employee.objects.create(
            first_name="Klaus", last_name="Betreuer"
        )
        self.student = Student.objects.create(
            first_name="Anna", last_name="Schüler", payer=self.payer
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
        self.supervision = Supervision.objects.create(
            student=self.student,
            caretaker=self.caretaker,
            school=self.school,
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 30),
            weekly_hours=timedelta(hours=5),
        )

    def test_calculator_page_get(self):
        """GET auf die Calculator-Seite liefert HTTP 200."""
        url = reverse(
            "admin:pedagogy_supervision_calculator", args=[self.supervision.pk]
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_calculator_404_for_missing_supervision(self):
        """GET mit nicht existierender pk liefert HTTP 404."""
        url = reverse("admin:pedagogy_supervision_calculator", args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_calculator_post_months_override(self):
        """POST mit months_override liefert HTTP 200 und verarbeitet den Wert."""
        url = reverse(
            "admin:pedagogy_supervision_calculator", args=[self.supervision.pk]
        )
        response = self.client.post(url, {"months_override": "2"})
        self.assertEqual(response.status_code, 200)

    def test_calculator_post_school_days_override(self):
        """POST mit school_days_override liefert HTTP 200 und verarbeitet den Wert."""
        url = reverse(
            "admin:pedagogy_supervision_calculator", args=[self.supervision.pk]
        )
        response = self.client.post(url, {"school_days_override": "10"})
        self.assertEqual(response.status_code, 200)

    def test_calculator_post_fee_agreement_override(self):
        """POST mit fee_agreement_override liefert HTTP 200 und nutzt das gewählte Agreement."""
        url = reverse(
            "admin:pedagogy_supervision_calculator", args=[self.supervision.pk]
        )
        response = self.client.post(
            url, {"fee_agreement_override": str(self.fee_agreement.pk)}
        )
        self.assertEqual(response.status_code, 200)

    def test_apply_total_redirects_to_calculator(self):
        """POST auf /apply-total/ speichert den Gesamtbetrag und leitet zurück zum Rechner."""
        url = reverse(
            "admin:pedagogy_supervision_calculator_apply_total",
            args=[self.supervision.pk],
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse(
                "admin:pedagogy_supervision_calculator", args=[self.supervision.pk]
            ),
            response["Location"],
        )

    def test_apply_installment_redirects_to_calculator(self):
        """POST auf /apply-installment/ speichert den Abschlag und leitet zurück zum Rechner."""
        url = reverse(
            "admin:pedagogy_supervision_calculator_apply_installment",
            args=[self.supervision.pk],
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse(
                "admin:pedagogy_supervision_calculator", args=[self.supervision.pk]
            ),
            response["Location"],
        )


class SupervisionRequestListViewTests(TestCase):
    """Smoke-Tests für die SupervisionRequestListView."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.test import Client

        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="union_admin", email="union@example.com", password="password"
        )
        self.client = Client()
        self.client.login(username="union_admin", password="password")

        self.payer = CostPayer.objects.create(identifier="Bezirk Union-Test")
        self.school = School.objects.create(name="Union-Testschule")
        self.caretaker = Employee.objects.create(
            first_name="Max", last_name="Mustermann"
        )
        self.student = Student.objects.create(
            first_name="Lisa", last_name="Listenkind", payer=self.payer
        )

    @property
    def url(self):
        return reverse("admin:pedagogy_supervision_request_list")

    def test_empty_list_returns_200(self):
        """Leere Datenbank: View liefert HTTP 200 ohne Fehler."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_list_with_supervision_returns_200(self):
        """View zeigt eine Betreuung korrekt an."""
        Supervision.objects.create(
            student=self.student,
            caretaker=self.caretaker,
            school=self.school,
            start_date=date(2024, 9, 1),
            end_date=date(2025, 6, 30),
            weekly_hours=timedelta(hours=5),
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_list_with_request_returns_200(self):
        """View zeigt einen Antrag korrekt an."""
        Request.objects.create(
            student=self.student,
            school=self.school,
            start_date=date(2024, 9, 1),
            demand=timedelta(hours=5),
            state=Request.State.DRAFT,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_list_with_mixed_data_returns_200(self):
        """View zeigt Betreuungen und Anträge gemischt an."""
        Supervision.objects.create(
            student=self.student,
            caretaker=self.caretaker,
            school=self.school,
            start_date=date(2024, 9, 1),
            end_date=date(2025, 6, 30),
            weekly_hours=timedelta(hours=5),
        )
        Request.objects.create(
            student=self.student,
            school=self.school,
            start_date=date(2024, 10, 1),
            demand=timedelta(hours=3),
            state=Request.State.APPROVED,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_filter_by_school_returns_200(self):
        """GET mit school-Filter liefert HTTP 200."""
        response = self.client.get(self.url, {"school": str(self.school.pk)})
        self.assertEqual(response.status_code, 200)

    def test_filter_by_date_range_returns_200(self):
        """GET mit Datumsbereich-Filter liefert HTTP 200."""
        response = self.client.get(
            self.url, {"start_date_from": "2024-01-01", "start_date_to": "2025-12-31"}
        )
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_redirects(self):
        """Nicht eingeloggter Zugriff wird auf Login weitergeleitet."""
        from django.test import Client

        anon = Client()
        response = anon.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])
