from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from finance.models import FeeAgreement, PoolAgreement
    from pedagogy.models import Supervision


def calculate_supervision_months(start_date: date, end_date: date) -> int:
    """Berechnet Betreuungsmonate (ganze Zahlen) mit 7-Tage-Regel.

    Start- und Endmonat zählen nur, wenn ≥7 Tage im jeweiligen Monat liegen.
    Mittlere Monate zählen immer voll. Minimum ist immer 1.
    """
    if (start_date.year, start_date.month) == (end_date.year, end_date.month):
        return 1

    days_in_start_month = calendar.monthrange(start_date.year, start_date.month)[1]
    days_remaining_in_start = days_in_start_month - start_date.day + 1
    start_count = 1 if days_remaining_in_start >= 7 else 0
    end_count = 1 if end_date.day >= 7 else 0

    middle_months = (
        (end_date.year - start_date.year) * 12 + end_date.month - start_date.month - 1
    )

    return max(1, start_count + middle_months + end_count)


@dataclass
class SupervisionCalculatorInput:
    supervision: Supervision
    months_override: Decimal | None = None
    school_days_override: int | None = None
    vacation_days_override: int | None = None
    public_holidays_override: int | None = None
    fee_agreement_override: FeeAgreement | None = None
    use_fee_agreement: bool = False


@dataclass
class SupervisionCalculatorResult:
    input: SupervisionCalculatorInput
    months: Decimal | None
    school_days: int | None
    school_days_breakdown: dict[str, int]
    fee_agreement: FeeAgreement | None
    pool_agreement: PoolAgreement | None
    calculated_total_amount: Decimal | None
    calculated_monthly_installment: Decimal | None
    is_pool_rate: bool
    is_tandem: bool = False
    warnings: list[str] = field(default_factory=list)


def run_supervision_calculation(
    inp: SupervisionCalculatorInput,
) -> SupervisionCalculatorResult:
    """Berechnet Gesamtbetrag und Abschlag für eine Betreuung. Einzige Funktion mit DB-Zugriff."""
    from finance.models import PoolAgreement

    warnings: list[str] = []
    sup = inp.supervision

    # Monate ermitteln
    calculated_months = sup.calculated_months
    months: Decimal = (
        inp.months_override
        if inp.months_override is not None
        else Decimal(calculated_months)
    )

    # Schultage-Breakdown ermitteln und Overrides anwenden
    from base.models import SchoolDays

    db_breakdown = SchoolDays.school_days_breakdown(sup.start_date, sup.end_date)
    effective_school_days = (
        inp.school_days_override
        if inp.school_days_override is not None
        else db_breakdown["school_days"]
    )
    effective_vacation_days = (
        inp.vacation_days_override
        if inp.vacation_days_override is not None
        else db_breakdown["vacation_days"]
    )
    effective_public_holidays = (
        inp.public_holidays_override
        if inp.public_holidays_override is not None
        else db_breakdown["public_holidays"]
    )
    effective_breakdown = {
        "school_days": effective_school_days,
        "vacation_days": effective_vacation_days,
        "public_holidays": effective_public_holidays,
        "total": effective_school_days
        + effective_vacation_days
        + effective_public_holidays,
    }
    school_days: int = effective_breakdown["total"]

    # Poolvereinbarung immer suchen
    pool = None
    if sup.student_id and sup.school_id:  # type: ignore[attr-defined]
        payer = sup.student.payer
        pool = PoolAgreement.objects.filter(
            payer=payer,
            school=sup.school,
            valid_from__lte=sup.start_date,
            valid_to__gte=sup.start_date,
        ).first()

    # Entgeltvereinbarung immer suchen (auch wenn Pool gefunden)
    fee = (
        inp.fee_agreement_override
        if inp.fee_agreement_override is not None
        else sup.fee_agreement
    )

    # Tandem-Status immer ermitteln (vor Pool/FEV-Split)
    from pedagogy.models import TandemPairing
    from django.db.models import Q

    is_tandem = (
        sup.pk is not None
        and TandemPairing.objects.filter(
            Q(supervision_a=sup) | Q(supervision_b=sup)
        ).exists()
    )

    # Entscheidung: Pool verwenden wenn vorhanden, nicht explizit FEV erzwungen,
    # und kein spezifischer FEV-Override gesetzt (Override impliziert FEV)
    use_pool = (
        pool is not None
        and not inp.use_fee_agreement
        and inp.fee_agreement_override is None
    )

    if use_pool:
        assert pool is not None
        total_amount = pool.flat_rate * months
        monthly_installment = pool.flat_rate
        return SupervisionCalculatorResult(
            input=inp,
            months=months,
            school_days=school_days,
            school_days_breakdown=effective_breakdown,
            fee_agreement=fee,
            pool_agreement=pool,
            calculated_total_amount=total_amount,
            calculated_monthly_installment=monthly_installment,
            is_pool_rate=True,
            is_tandem=is_tandem,
            warnings=warnings,
        )

    # Stündliche Abrechnung via Entgeltvereinbarung
    if fee is None:
        warnings.append(
            f"Keine Entgeltvereinbarung für Kostenträger und Startdatum"
            f" {sup.start_date.strftime('%d.%m.%Y')} gefunden."
        )

    # Jahresstunden inline berechnen
    daily_hours = sup.daily_hours
    if daily_hours is None:
        warnings.append("Wochenstunden fehlen — Jahresstunden nicht berechenbar.")

    total_amount = None
    monthly_installment = None

    if fee is not None and daily_hours is not None and school_days is not None:
        yearly_hours_dec = Decimal((daily_hours * school_days).total_seconds() / 3600)
        price = fee.price_tandem if is_tandem else fee.price_standard
        total_amount = price * yearly_hours_dec
        if is_tandem:
            total_amount = total_amount * Decimal("0.5")
        monthly_installment = total_amount / months

    return SupervisionCalculatorResult(
        input=inp,
        months=months,
        school_days=school_days,
        school_days_breakdown=effective_breakdown,
        fee_agreement=fee,
        pool_agreement=pool,
        calculated_total_amount=total_amount,
        calculated_monthly_installment=monthly_installment,
        is_pool_rate=False,
        is_tandem=is_tandem,
        warnings=warnings,
    )
