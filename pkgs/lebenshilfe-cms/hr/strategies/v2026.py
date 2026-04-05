from __future__ import annotations

import calendar
from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING

from base.calculated_fields.types import CalculationEntry
from hr.strategies.base import CalculationStrategy

if TYPE_CHECKING:
    from hr.models import Employment


class V2026Strategy(CalculationStrategy):
    """
    Calculation rules current as of 2026.
    Direct translation of the legacy @property methods on Employment.
    """

    @classmethod
    def field_schema(cls) -> dict[str, CalculationEntry]:
        return {
            "salary_agreement": CalculationEntry(
                value=None,
                label="Gehaltsvereinbarung",
                field_type="text",
                overridable=False,
                override_key=None,
            ),
            "work_days": CalculationEntry(
                value=None,
                label="Arbeitstage (rechnerisch)",
                field_type="integer",
                overridable=True,
                override_key="work_days",
            ),
            "months": CalculationEntry(
                value=None,
                label="Monate (rechnerisch)",
                field_type="decimal",
                overridable=True,
                override_key="months",
            ),
            "gross_salary": CalculationEntry(
                value=None,
                label="Brutto laut Vertrag (rechnerisch)",
                field_type="euro",
                overridable=True,
                override_key="gross_salary",
            ),
            "yearly_gross_salary": CalculationEntry(
                value=None,
                label="Jahresbrutto (rechnerisch)",
                field_type="euro",
                overridable=False,
                override_key=None,
            ),
        }

    def calculate(self, employment: Employment) -> dict[str, CalculationEntry]:
        overrides = employment.overrides or {}

        salary_agreement = self._salary_agreement(employment)
        work_days_calc = self._work_days(employment)
        months_calc = self._months(employment)
        gross_salary_calc = self._gross_salary(employment, salary_agreement)

        effective_months = (
            Decimal(str(overrides["months"])) if "months" in overrides else months_calc
        )
        effective_gross = (
            Decimal(str(overrides["gross_salary"]))
            if "gross_salary" in overrides
            else gross_salary_calc
        )
        yearly = self._yearly(effective_gross, effective_months)

        return {
            "salary_agreement": CalculationEntry(
                value=str(salary_agreement) if salary_agreement else None,
                label="Gehaltsvereinbarung",
                field_type="text",
                overridable=False,
                override_key=None,
            ),
            "work_days": CalculationEntry(
                value=work_days_calc,
                label="Arbeitstage (rechnerisch)",
                field_type="integer",
                overridable=True,
                override_key="work_days",
            ),
            "months": CalculationEntry(
                value=months_calc,
                label="Monate (rechnerisch)",
                field_type="decimal",
                overridable=True,
                override_key="months",
            ),
            "gross_salary": CalculationEntry(
                value=gross_salary_calc,
                label="Brutto laut Vertrag (rechnerisch)",
                field_type="euro",
                overridable=True,
                override_key="gross_salary",
            ),
            "yearly_gross_salary": CalculationEntry(
                value=yearly,
                label="Jahresbrutto (rechnerisch)",
                field_type="euro",
                overridable=False,
                override_key=None,
            ),
        }

    # ------------------------------------------------------------------
    # Private calculation helpers (migrated from Employment @property methods)
    # ------------------------------------------------------------------

    def _salary_agreement(self, emp: Employment):
        from finance.models import SalaryAgreement

        return SalaryAgreement.objects.filter(
            valid_from__lte=emp.start_date,
            valid_to__gte=emp.start_date,
        ).first()

    def _work_days(self, emp: Employment) -> int | None:
        if emp.end_date is None:
            return None
        from base.models import SchoolDays

        return SchoolDays.total_school_days(emp.start_date, emp.end_date)

    def _months(self, emp: Employment) -> Decimal | None:
        if emp.end_date is None:
            return None
        whole_months = (emp.end_date.year - emp.start_date.year) * 12 + (
            emp.end_date.month - emp.start_date.month
        )
        day_diff = emp.end_date.day - emp.start_date.day
        if day_diff >= 0:
            days_in_month = calendar.monthrange(emp.end_date.year, emp.end_date.month)[
                1
            ]
            fraction = Decimal(day_diff) / Decimal(days_in_month)
        else:
            whole_months -= 1
            prev_month = emp.end_date.month - 1 or 12
            prev_year = (
                emp.end_date.year if emp.end_date.month > 1 else emp.end_date.year - 1
            )
            days_in_month = calendar.monthrange(prev_year, prev_month)[1]
            fraction = Decimal(days_in_month + day_diff) / Decimal(days_in_month)
        return (
            ((Decimal(whole_months) + fraction) * Decimal("2")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
            / Decimal("2")
        ).quantize(Decimal("0.1"))

    def _gross_salary(self, emp: Employment, agreement) -> Decimal | None:
        if emp.weekly_hours is None:
            return None
        if not agreement or not emp.contract_type:
            return None
        from hr.models import Employment

        rate_map = {
            Employment.ContractType.SCHOOL_ACCOMPANIMENT: agreement.salary_standard,
            Employment.ContractType.TANDEM: agreement.salary_tandem,
            Employment.ContractType.SCHOOL_ACCOMPANIMENT_HONORARY: agreement.salary_honorary_standard,
            Employment.ContractType.TANDEM_HONORARY: agreement.salary_honorary_tandem,
            Employment.ContractType.COORDINATION: agreement.salary_coordination,
            Employment.ContractType.MANAGEMENT: agreement.salary_management,
        }
        rate = rate_map.get(emp.contract_type)
        if rate is None:
            return None
        weekly_hours_dec = Decimal(emp.weekly_hours.total_seconds() / 3600)
        return (rate * weekly_hours_dec * Decimal("4")).quantize(
            Decimal("1E+1"), rounding=ROUND_HALF_UP
        )

    def _yearly(self, gross: Decimal | None, months: Decimal | None) -> Decimal | None:
        if gross is None or months is None:
            return None
        return gross * months
