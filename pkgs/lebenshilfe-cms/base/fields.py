from django.db import models
from .widgets import EuroDecimalWidget, HourMinuteDurationWidget

class EuroDecimalField(models.DecimalField):
    def formfield(self, **kwargs):
        kwargs["widget"] = EuroDecimalWidget
        return super().formfield(**kwargs)

class HourMinuteDurationField(models.DurationField):
    def formfield(self, **kwargs):
        kwargs["widget"] = HourMinuteDurationWidget
        return super().formfield(**kwargs)
