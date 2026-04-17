import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class CalculatorInput:
    start_date: date
    end_date: date | None
    weekly_hours: timedelta
    contract_type: str
    months_override: Decimal | None = None
    salary_agreement_override: object | None = None  # finance.models.SalaryAgreement


@dataclass
class CalculatorResult:
    input: CalculatorInput
    salary_agreement: object | None  # finance.models.SalaryAgreement
    calculated_months: Decimal | None
    effective_months: Decimal | None
    monthly_gross_salary: Decimal | None
    yearly_gross_salary: Decimal | None
    warnings: list[str] = field(default_factory=list)


def calculate_months(start_date: date, end_date: date) -> Decimal:
    """Berechnet Vertragsmonate als Dezimalzahl, gerundet auf 0.5."""
    whole_months = (end_date.year - start_date.year) * 12 + (
        end_date.month - start_date.month
    )
    day_diff = end_date.day - start_date.day
    if day_diff >= 0:
        days_in_month = calendar.monthrange(end_date.year, end_date.month)[1]
        fraction = Decimal(day_diff) / Decimal(days_in_month)
    else:
        whole_months -= 1
        prev_month = end_date.month - 1 or 12
        prev_year = end_date.year if end_date.month > 1 else end_date.year - 1
        days_in_month = calendar.monthrange(prev_year, prev_month)[1]
        fraction = Decimal(days_in_month + day_diff) / Decimal(days_in_month)
    return (
        ((Decimal(whole_months) + fraction) * Decimal("2")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        / Decimal("2")
    ).quantize(Decimal("0.1"))


def get_salary_rate(agreement, contract_type: str) -> Decimal | None:
    """Gibt den Stundensatz für den gegebenen Vertragstyp zurück."""
    from hr.models import Employment

    rate_map: dict[str, Decimal | None] = {
        Employment.ContractType.SCHOOL_ACCOMPANIMENT: agreement.salary_standard,
        Employment.ContractType.TANDEM: agreement.salary_tandem,
        Employment.ContractType.SCHOOL_ACCOMPANIMENT_HONORARY: agreement.salary_honorary_standard,
        Employment.ContractType.TANDEM_HONORARY: agreement.salary_honorary_tandem,
        Employment.ContractType.COORDINATION: agreement.salary_coordination,
        Employment.ContractType.MANAGEMENT: agreement.salary_management,
    }
    return rate_map.get(contract_type)


def calculate_monthly_gross(rate: Decimal, weekly_hours: timedelta) -> Decimal:
    """Berechnet das monatliche Brutto: rate × Wochenstunden × 4, auf 10 € gerundet."""
    weekly_hours_dec = Decimal(weekly_hours.total_seconds() / 3600)
    return (rate * weekly_hours_dec * Decimal("4")).quantize(
        Decimal("1E+1"), rounding=ROUND_HALF_UP
    )


def calculate_yearly_gross(
    monthly_gross: Decimal, effective_months: Decimal
) -> Decimal:
    """Berechnet das Jahresbrutto."""
    return monthly_gross * effective_months


def run_calculation(inp: CalculatorInput) -> CalculatorResult:
    """Führt die vollständige Gehaltsberechnung durch. Einzige Funktion mit DB-Zugriff."""
    from finance.models import SalaryAgreement

    warnings: list[str] = []

    # Gehaltsvereinbarung ermitteln
    if inp.salary_agreement_override is not None:
        agreement = inp.salary_agreement_override
    else:
        agreement = SalaryAgreement.objects.filter(
            valid_from__lte=inp.start_date,
            valid_to__gte=inp.start_date,
        ).first()
        if agreement is None:
            warnings.append(
                f"Kein Tarifvertrag für Startdatum {inp.start_date.strftime('%d.%m.%Y')} gefunden."
            )

    # Monate
    calculated_months: Decimal | None = None
    if inp.end_date is not None:
        calculated_months = calculate_months(inp.start_date, inp.end_date)
    else:
        warnings.append("Kein Enddatum angegeben — Jahresbrutto nicht berechenbar.")

    effective_months: Decimal | None = (
        inp.months_override if inp.months_override is not None else calculated_months
    )

    # Monatsbrutto
    monthly_gross: Decimal | None = None
    if agreement and inp.contract_type:
        rate = get_salary_rate(agreement, inp.contract_type)
        if rate is None:
            warnings.append(
                f"Kein Stundensatz für Vertragstyp '{inp.contract_type}' gefunden."
            )
        else:
            monthly_gross = calculate_monthly_gross(rate, inp.weekly_hours)

    # Jahresbrutto
    yearly_gross: Decimal | None = None
    if monthly_gross is not None and effective_months is not None:
        yearly_gross = calculate_yearly_gross(monthly_gross, effective_months)

    return CalculatorResult(
        input=inp,
        salary_agreement=agreement,
        calculated_months=calculated_months,
        effective_months=effective_months,
        monthly_gross_salary=monthly_gross,
        yearly_gross_salary=yearly_gross,
        warnings=warnings,
    )
