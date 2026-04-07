from datetime import timedelta
from decimal import Decimal

from django import forms
from django.contrib.admin.widgets import AdminDateWidget
from unfold.widgets import INPUT_CLASSES

from base.widgets import HourMinuteDurationWidget
from hr.models import Employment


class HourMinuteDurationFormField(forms.DurationField):
    widget = HourMinuteDurationWidget

    def clean(self, value):
        if isinstance(value, timedelta):
            return value
        return super().clean(value)


class SalaryCalculatorForm(forms.Form):
    start_date = forms.DateField(
        label="Beginn Arbeitsverhältnis",
        widget=AdminDateWidget,
    )
    end_date = forms.DateField(
        label="Ende Arbeitsverhältnis",
        required=False,
        widget=AdminDateWidget,
    )
    weekly_hours = HourMinuteDurationFormField(
        label="Wochenstunden",
    )
    contract_type = forms.ChoiceField(
        label="Art des Vertrags",
        choices=[("", "---------")] + list(Employment.ContractType.choices),
        widget=forms.Select(attrs={"class": " ".join(INPUT_CLASSES)}),
    )
    month_override = forms.DecimalField(
        label="Monate (Überschreibung)",
        required=False,
        min_value=Decimal("0.5"),
        decimal_places=1,
        max_digits=5,
        widget=forms.NumberInput(
            attrs={
                "class": " ".join(INPUT_CLASSES),
                "step": "0.5",
                "placeholder": "z. B. 1.5",
            }
        ),
    )
    work_days_override = forms.IntegerField(
        label="Arbeitstage (Überschreibung)",
        required=False,
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "class": " ".join(INPUT_CLASSES),
                "placeholder": "z. B. 20",
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            raise forms.ValidationError(
                "Das Enddatum darf nicht vor dem Startdatum liegen."
            )
        return cleaned
