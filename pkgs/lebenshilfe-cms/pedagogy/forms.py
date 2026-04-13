from decimal import Decimal

from django import forms
from django.db.models import QuerySet
from django.urls import reverse
from unfold.widgets import (
    INPUT_CLASSES,
    UnfoldAdminDateWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminSelectWidget,
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
                "placeholder": "z. B. 185",
                "class": " ".join(INPUT_CLASSES),
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
                "step": "0.5",
                "placeholder": "z. B. 10",
                "class": " ".join(INPUT_CLASSES),
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

    @property
    def media(self):
        return super().media + forms.Media(js=[reverse("javascript-catalog")])


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
        widget=UnfoldAdminDateWidget(),
    )
    start_date_to = forms.DateField(
        required=False,
        label="Bis",
        widget=UnfoldAdminDateWidget(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from pedagogy.models import School

        self.fields["school"].queryset = School.objects.order_by("name")

    @property
    def media(self):
        return super().media + forms.Media(js=[reverse("javascript-catalog")])

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
