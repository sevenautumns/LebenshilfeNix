from decimal import Decimal

from django import forms
from django.db.models import QuerySet
from unfold.widgets import (
    INPUT_CLASSES,
    UnfoldAdminSelect2Widget,
    UnfoldAdminSelectWidget,
    UnfoldAdminSingleDateWidget,
)


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
    use_fee_agreement = forms.BooleanField(
        label="Entgeltvereinbarung erzwingen (statt Poolvereinbarung)",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from finance.models import FeeAgreement

        self.fields["fee_agreement_override"].queryset = FeeAgreement.objects.order_by(
            "-valid_from"
        )


class SupervisionRequestFilterForm(forms.Form):
    school = forms.ModelChoiceField(
        queryset=None,  # gesetzt in __init__
        required=False,
        label="Schule",
        empty_label="— Alle Schulen —",
        widget=UnfoldAdminSelectWidget(),
    )
    start_date_from = forms.DateField(
        required=False,
        label="Von",
        widget=UnfoldAdminSingleDateWidget(),
    )
    start_date_to = forms.DateField(
        required=False,
        label="Bis",
        widget=UnfoldAdminSingleDateWidget(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from pedagogy.models import School

        self.fields["school"].queryset = School.objects.order_by("name")

    def filter_queryset(self, qs: QuerySet) -> QuerySet:
        if not self.is_valid():
            return qs
        if school := self.cleaned_data.get("school"):
            qs = qs.filter(school=school)
        if from_date := self.cleaned_data.get("start_date_from"):
            qs = qs.filter(start_date__gte=from_date)
        if to_date := self.cleaned_data.get("start_date_to"):
            qs = qs.filter(start_date__lte=to_date)
        return qs
