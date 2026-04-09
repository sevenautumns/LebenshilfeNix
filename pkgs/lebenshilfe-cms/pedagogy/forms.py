from decimal import Decimal

from django import forms
from unfold.widgets import INPUT_CLASSES, UnfoldAdminSelect2Widget


class SupervisionCalculatorOverridesForm(forms.Form):
    fee_agreement_override = forms.ModelChoiceField(
        label="Entgeltvereinbarung (Überschreibung)",
        queryset=None,  # gesetzt in __init__
        required=False,
        empty_label="— automatisch nach Kostenträger + Startdatum —",
        widget=UnfoldAdminSelect2Widget(),
    )
    school_days_override = forms.IntegerField(
        label="Schultage (Überschreibung)",
        required=False,
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": " ".join(INPUT_CLASSES),
                "placeholder": "z. B. 185",
            }
        ),
    )
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from finance.models import FeeAgreement

        self.fields["fee_agreement_override"].queryset = FeeAgreement.objects.order_by(
            "-valid_from"
        )
