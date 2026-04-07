from decimal import Decimal

from django import forms
from unfold.widgets import INPUT_CLASSES


class CalculatorOverridesForm(forms.Form):
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
