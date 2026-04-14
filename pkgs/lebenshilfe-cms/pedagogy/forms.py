from datetime import date
from decimal import Decimal

from django import forms
from django.db.models import QuerySet
from unfold.widgets import (
    INPUT_CLASSES,
    UnfoldAdminDateWidget,
    UnfoldAdminSelect2Widget,
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


def _school_year_bounds() -> tuple[date, date]:
    today = date.today()
    if today.month >= 8:
        return date(today.year, 8, 1), date(today.year + 1, 7, 31)
    return date(today.year - 1, 8, 1), date(today.year, 7, 31)


class SupervisionRequestFilterForm(forms.Form):
    from pedagogy.models import Request

    school = forms.ModelChoiceField(
        queryset=None,  # gesetzt in __init__
        required=False,
        label="Schule",
        empty_label="— Alle Schulen —",
        widget=UnfoldAdminSelect2Widget(),
    )
    start_date_from = forms.DateField(
        required=False,
        label="Startdatum von",
        widget=UnfoldAdminDateWidget(),
    )
    start_date_to = forms.DateField(
        required=False,
        label="Startdatum bis",
        widget=UnfoldAdminDateWidget(),
    )
    state = forms.ChoiceField(
        choices=[("", "— Alle Zustände —")] + Request.State.choices,
        required=False,
        label="Zustand (Anträge)",
        widget=UnfoldAdminSelect2Widget(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from pedagogy.models import School, Request

        self.fields["school"].queryset = School.objects.order_by("name")
        start, end = _school_year_bounds()
        self.fields["start_date_from"].initial = start
        self.fields["start_date_to"].initial = end
        self.fields["state"].initial = Request.State.IN_REVIEW

    def filter_queryset(self, qs: QuerySet) -> QuerySet:
        from pedagogy.models import Request

        is_request_qs = qs.model is Request

        if not self.is_valid():
            # Ungebunden (erster Aufruf / nach "Zurücksetzen") → Schuljahr- und Zustandsdefault
            start, end = _school_year_bounds()
            qs = qs.filter(start_date__gte=start, start_date__lte=end)
            if is_request_qs:
                qs = qs.filter(state=Request.State.IN_REVIEW)
            return qs

        if school := self.cleaned_data.get("school"):
            qs = qs.filter(school=school)
        if from_date := self.cleaned_data.get("start_date_from"):
            qs = qs.filter(start_date__gte=from_date)
        if to_date := self.cleaned_data.get("start_date_to"):
            qs = qs.filter(start_date__lte=to_date)
        if is_request_qs:
            if state := self.cleaned_data.get("state"):
                qs = qs.filter(state=state)
        return qs
