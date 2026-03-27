from django.db import models
from .widgets import EuroDecimalWidget, HourMinuteDurationWidget
from django.utils import formats


class EuroDecimalField(models.DecimalField):
    def formfield(self, **kwargs):
        kwargs["widget"] = EuroDecimalWidget
        return super().formfield(**kwargs)

    def get_admin_format(self, value):
        if value is None:
            return "-"
        formatted = formats.number_format(value, decimal_pos=2, use_l10n=True)
        return f"{formatted} €"


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
