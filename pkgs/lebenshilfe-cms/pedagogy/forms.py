from decimal import Decimal

from django import forms
from unfold.widgets import INPUT_CLASSES


class SupervisionCalculatorOverridesForm(forms.Form):
    months_override = forms.DecimalField(
        label="Monate (Überschreibung)",
        required=False,
        min_value=Decimal("1"),
        decimal_places=1,
        max_digits=5,
        widget=forms.NumberInput(
            attrs={
                "class": " ".join(INPUT_CLASSES),
                "step": "0.5",
                "placeholder": "z. B. 10",
            }
        ),
    )
