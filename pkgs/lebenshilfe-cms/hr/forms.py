from decimal import Decimal

from django import forms
from unfold.widgets import INPUT_CLASSES, UnfoldAdminSelect2Widget


class CalculatorOverridesForm(forms.Form):
    salary_agreement_override = forms.ModelChoiceField(
        label="Tarifvertrag (Überschreibung)",
        queryset=None,  # gesetzt in __init__
        required=False,
        empty_label="— automatisch nach Startdatum —",
        widget=UnfoldAdminSelect2Widget(),
    )
    months_override = forms.DecimalField(
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from finance.models import SalaryAgreement

        self.fields[
            "salary_agreement_override"
        ].queryset = SalaryAgreement.objects.order_by("-valid_from")  # type: ignore[attr-defined]
