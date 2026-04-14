import calendar
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


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
    supervision: object  # pedagogy.models.Supervision
    months_override: Decimal | None = None
    school_days_override: int | None = None
    fee_agreement_override: object | None = None  # finance.models.FeeAgreement
    use_fee_agreement: bool = False


@dataclass
class SupervisionCalculatorResult:
    input: SupervisionCalculatorInput
    months: Decimal | None
    school_days: int | None
    fee_agreement: object | None  # finance.models.FeeAgreement
    pool_agreement: object | None  # finance.models.PoolAgreement
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

    # Schultage ermitteln
    school_days: int | None = (
        inp.school_days_override
        if inp.school_days_override is not None
        else sup.calculated_school_days
    )

    # Poolvereinbarung immer suchen
    pool = None
    if sup.student_id and sup.school_id:
        try:
            payer = sup.student.payer
        except Exception:
            payer = None
        if payer is not None:
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
        total_amount = pool.flat_rate * months
        monthly_installment = pool.flat_rate
        return SupervisionCalculatorResult(
            input=inp,
            months=months,
            school_days=school_days,
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
        fee_agreement=fee,
        pool_agreement=pool,
        calculated_total_amount=total_amount,
        calculated_monthly_installment=monthly_installment,
        is_pool_rate=False,
        is_tandem=is_tandem,
        warnings=warnings,
    )
