from datetime import date
from decimal import Decimal

from django import forms
from django.db.models import QuerySet
from unfold.widgets import (
    INPUT_CLASSES,
    UnfoldAdminDateWidget,
    UnfoldAdminSelect2Widget,
)

from finance.models import FeeAgreement
from pedagogy.models import Request, School


class SupervisionCalculatorOverridesForm(forms.Form):
    fee_agreement_override = forms.ModelChoiceField(
        label="Entgeltvereinbarung (Überschreibung)",
        queryset=FeeAgreement.objects.order_by("-valid_from"),
        required=False,
        empty_label="— automatisch nach Kostenträger + Startdatum —",
        widget=UnfoldAdminSelect2Widget(),
    )
    school_days_override = forms.IntegerField(
        label="Schultage (Überschreibung)",
        required=False,
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "z. B. 56",
                "class": " ".join(INPUT_CLASSES),
            }
        ),
    )
    vacation_days_override = forms.IntegerField(
        label="Urlaubstage (Überschreibung)",
        required=False,
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "z. B. 5",
                "class": " ".join(INPUT_CLASSES),
            }
        ),
    )
    public_holidays_override = forms.IntegerField(
        label="Feiertage (Überschreibung)",
        required=False,
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "z. B. 2",
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


def _school_year_bounds() -> tuple[date, date]:
    today = date.today()
    if today.month >= 8:
        return date(today.year, 8, 1), date(today.year + 1, 7, 31)
    return date(today.year - 1, 8, 1), date(today.year, 7, 31)


class NewRequestFilterForm(forms.Form):
    school = forms.ModelChoiceField(
        queryset=School.objects.order_by("name"),
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
        start, end = _school_year_bounds()
        self.fields["start_date_from"].initial = start
        self.fields["start_date_to"].initial = end
        self.fields["state"].initial = Request.State.IN_REVIEW

    def _filter_common(self, qs: QuerySet) -> QuerySet:
        """Gemeinsame Filter die für beide Modelle gelten (Schule, Datumsspanne)."""
        if not self.is_valid():
            start, end = _school_year_bounds()
            return qs.filter(start_date__gte=start, start_date__lte=end)
        if school := self.cleaned_data.get("school"):
            qs = qs.filter(school=school)
        if from_date := self.cleaned_data.get("start_date_from"):
            qs = qs.filter(start_date__gte=from_date)
        if to_date := self.cleaned_data.get("start_date_to"):
            qs = qs.filter(start_date__lte=to_date)
        return qs

    def filter_queryset_a(self, qs: QuerySet) -> QuerySet:
        """Filter für Betreuungen — kein Zustandsfilter."""
        return self._filter_common(qs)

    def filter_queryset_b(self, qs: QuerySet) -> QuerySet:
        """Filter für Anträge — inkl. Zustandsfilter."""
        qs = self._filter_common(qs)
        if not self.is_valid():
            return qs.filter(state=Request.State.IN_REVIEW)
        if state := self.cleaned_data.get("state"):
            qs = qs.filter(state=state)
        return qs
