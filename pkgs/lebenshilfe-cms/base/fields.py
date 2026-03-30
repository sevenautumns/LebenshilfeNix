from django.db import models
from .widgets import EuroDecimalWidget, HourMinuteDurationWidget, MonthWidget
from django.utils import formats
from datetime import date


class EuroDecimalField(models.DecimalField):
    def formfield(self, **kwargs):
        kwargs["widget"] = EuroDecimalWidget
        return super().formfield(**kwargs)

    def get_admin_format(self, value):
        if value is None:
            return "-"
        formatted = formats.number_format(value, decimal_pos=2, use_l10n=True)
        return f"{formatted} €"


class MonthField(models.DateField):
    """DateField that stores only year+month (always normalized to the 1st of the month)."""

    def formfield(self, **kwargs):
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
    def formfield(self, **kwargs):
        kwargs["widget"] = HourMinuteDurationWidget
        return super().formfield(**kwargs)

    def get_admin_format(self, value):
        if not value:
            return "-"
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes = remainder // 60
        return f"{hours}:{minutes:02d} Std."
