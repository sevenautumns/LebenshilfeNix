from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class SupervisionCalculatorInput:
    supervision: object  # pedagogy.models.Supervision
    months_override: Decimal | None = None


@dataclass
class SupervisionCalculatorResult:
    months: Decimal | None
    fee_agreement: object | None  # finance.models.FeeAgreement
    pool_agreement: object | None  # finance.models.PoolAgreement
    calculated_total_amount: Decimal | None
    calculated_monthly_installment: Decimal | None
    is_pool_rate: bool
    warnings: list[str] = field(default_factory=list)


def run_supervision_calculation(
    inp: SupervisionCalculatorInput,
) -> SupervisionCalculatorResult:
    """Berechnet Gesamtbetrag und Abschlag für eine Betreuung. Einzige Funktion mit DB-Zugriff."""
    from finance.models import FeeAgreement, PoolAgreement

    warnings: list[str] = []
    sup = inp.supervision

    # Monate ermitteln
    calculated_months = sup.calculated_months
    months: Decimal = (
        inp.months_override
        if inp.months_override is not None
        else Decimal(calculated_months)
    )

    # Poolvereinbarung prüfen
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

    if pool is not None:
        total_amount = pool.flat_rate * months
        monthly_installment = pool.flat_rate
        return SupervisionCalculatorResult(
            months=months,
            fee_agreement=None,
            pool_agreement=pool,
            calculated_total_amount=total_amount,
            calculated_monthly_installment=monthly_installment,
            is_pool_rate=True,
            warnings=warnings,
        )

    # Entgeltvereinbarung (FEV) — stündliche Abrechnung
    fee = sup.fee_agreement
    if fee is None:
        warnings.append(
            f"Keine Entgeltvereinbarung für Kostenträger und Startdatum"
            f" {sup.start_date.strftime('%d.%m.%Y')} gefunden."
        )

    if sup.yearly_hours is None:
        warnings.append(
            "Jahresstunden nicht berechenbar — Betreuungsstunden oder Schultage fehlen."
        )

    total_amount = None
    monthly_installment = None

    if fee is not None and sup.yearly_hours is not None:
        price = fee.price_tandem if sup.tandem_id else fee.price_standard
        yearly_hours_dec = Decimal(sup.yearly_hours.total_seconds() / 3600)
        total_amount = price * yearly_hours_dec
        monthly_installment = total_amount / months

    return SupervisionCalculatorResult(
        months=months,
        fee_agreement=fee,
        pool_agreement=None,
        calculated_total_amount=total_amount,
        calculated_monthly_installment=monthly_installment,
        is_pool_rate=False,
        warnings=warnings,
    )
