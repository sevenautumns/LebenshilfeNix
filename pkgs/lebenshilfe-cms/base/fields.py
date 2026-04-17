from django.db import models
from .widgets import EuroDecimalWidget, HourMinuteDurationWidget, MonthWidget
from django.utils import formats
from datetime import date, timedelta


class EuroDecimalField(models.DecimalField):
    def formfield(self, form_class=None, choices_form_class=None, **kwargs):
        kwargs["widget"] = EuroDecimalWidget
        return super().formfield(**kwargs)

    def get_admin_format(self, value):
        if value is None:
            return "-"
        formatted = formats.number_format(value, decimal_pos=2, use_l10n=True)
        return f"{formatted} €"


class MonthField(models.DateField):
    """DateField that stores only year+month (always normalized to the 1st of the month)."""

    def formfield(self, form_class=None, choices_form_class=None, **kwargs):
        kwargs["widget"] = MonthWidget
        return super().formfield(**kwargs)

    def to_python(self, value):
        if isinstance(value, date):
            return value.replace(day=1)
        return super().to_python(value)

    def get_admin_format(self, value):
        if value is None:
            return "-"
        return value.strftime("%m/%Y")


class HourMinuteDurationField(models.DurationField):
    def formfield(self, form_class=None, choices_form_class=None, **kwargs):
        kwargs["widget"] = HourMinuteDurationWidget
        return super().formfield(**kwargs)

    @staticmethod
    def to_hours_minutes(value: timedelta) -> tuple[int, int]:
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        return hours, remainder // 60

    @staticmethod
    def format_std(value: timedelta) -> str:
        hours, minutes = HourMinuteDurationField.to_hours_minutes(value)
        return f"{hours}:{minutes:02d} Std."

    def get_admin_format(self, value):
        if not value:
            return "-"
        return HourMinuteDurationField.format_std(value)
