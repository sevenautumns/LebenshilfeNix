from urllib.parse import urlencode

from django.contrib import admin, messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.formats import number_format
from django.utils.html import format_html
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import action, display
from unfold.enums import ActionVariant

from base.admin import BaseModelAdmin, AddressInline, PhoneInline, EmailInline
from base.admin_views import BaseApplyView, BaseCalculatorView
from base.fields import EuroDecimalField

from .models import School, Student, Supervision, Request

_euro_fmt = EuroDecimalField(max_digits=10, decimal_places=2)


class SupervisionCalculatorView(BaseCalculatorView):
    title = "Betreuungsrechner"

    def get_queryset(self):
        return Supervision.objects.select_related(
            "student", "student__payer", "caretaker", "school", "tandem"
        )

    @classmethod
    def parse_overrides(cls, data: dict) -> dict:
        """Parst Override-Werte aus GET/POST-Daten."""
        from decimal import Decimal
        from finance.models import FeeAgreement

        overrides = {}
        if mo := data.get("months_override"):
            try:
                overrides["months_override"] = Decimal(mo)
            except Exception:
                pass
        if sd := data.get("school_days_override"):
            try:
                overrides["school_days_override"] = int(sd)
            except Exception:
                pass
        if fev_pk := data.get("fee_agreement_override"):
            try:
                overrides["fee_agreement_override"] = FeeAgreement.objects.get(
                    pk=int(fev_pk)
                )
            except Exception:
                pass
        return overrides

    @classmethod
    def overrides_to_params(cls, overrides: dict) -> dict:
        params = {}
        if mo := overrides.get("months_override"):
            params["months_override"] = str(mo)
        if sd := overrides.get("school_days_override"):
            params["school_days_override"] = str(sd)
        if fa := overrides.get("fee_agreement_override"):
            params["fee_agreement_override"] = str(fa.pk)
        return params

    def get_source_fields(self, obj: Supervision):
        from base.fields import HourMinuteDurationField as HMField

        return [
            ("Schüler:in", str(obj.student)),
            (
                "Kostenträger",
                str(obj.student.payer) if obj.student_id else "—",
            ),
            ("Schule", str(obj.school)),
            (
                "Zeitraum",
                f"{obj.start_date.strftime('%d.%m.%Y')} – {obj.end_date.strftime('%d.%m.%Y')}",
            ),
            (
                "Wochenstunden",
                HMField.format_std(obj.weekly_hours),
            ),
            ("Schultage (rechnerisch)", obj.calculated_school_days),
        ]

    def get_primary_results(self, obj: Supervision, result):
        i = result.input
        override_params = self.overrides_to_params(
            {
                "months_override": i.months_override,
                "school_days_override": i.school_days_override,
                "fee_agreement_override": i.fee_agreement_override,
            }
        )

        def _apply_url(url_name):
            url = reverse(url_name, args=[obj.pk])
            if override_params:
                url += "?" + urlencode(override_params)
            return url

        apply_total_url = _apply_url(
            "admin:pedagogy_supervision_calculator_apply_total"
        )
        apply_installment_url = _apply_url(
            "admin:pedagogy_supervision_calculator_apply_installment"
        )

        return [
            {
                "label": "Gesamtbetrag (berechnet)",
                "value": result.calculated_total_amount,
                "unit": "€",
                "stored_label": "Gespeicherter Gesamtbetrag",
                "stored_value": obj.total_amount,
                "apply_url": apply_total_url
                if result.calculated_total_amount is not None
                else None,
            },
            {
                "label": "Abschlag pro Monat (berechnet)",
                "value": result.calculated_monthly_installment,
                "unit": "€",
                "stored_label": "Gespeicherter Abschlag",
                "stored_value": obj.monthly_installment,
                "apply_url": apply_installment_url
                if result.calculated_monthly_installment is not None
                else None,
            },
        ]

    def get_result_rows(self, obj: Supervision, result):
        i = result.input
        rows = []
        if result.is_pool_rate and result.pool_agreement:
            rows.append(("Abrechnungsart", "Pauschale (Poolvereinbarung)", True))
            rows.append(("Poolvereinbarung", str(result.pool_agreement), False))
        else:
            rows.append(
                (
                    "Entgeltvereinbarung",
                    str(result.fee_agreement) if result.fee_agreement else "—",
                    i.fee_agreement_override is not None,
                )
            )
        rows += [
            (
                "Schultage (effektiv)",
                result.school_days,
                i.school_days_override is not None,
            ),
            ("Monate (rechnerisch)", obj.calculated_months, False),
            (
                "Effektive Monate",
                result.months,
                result.months != obj.calculated_months,
            ),
        ]
        return rows

    def _render_calculator(self, supervision: Supervision, form, **overrides):
        from .calculators import SupervisionCalculatorInput, run_supervision_calculation

        result = run_supervision_calculation(
            SupervisionCalculatorInput(supervision=supervision, **overrides)
        )

        return self.render_to_response(
            self.get_context_data(obj=supervision, result=result, form=form)
        )

    def get(self, request, *args, **kwargs):
        from .forms import SupervisionCalculatorOverridesForm

        supervision = self.get_object()
        overrides = self.parse_overrides(request.GET)
        form = SupervisionCalculatorOverridesForm(initial=overrides or None)
        return self._render_calculator(supervision, form, **overrides)

    def post(self, request, *args, **kwargs):
        from .forms import SupervisionCalculatorOverridesForm

        supervision = self.get_object()
        form = SupervisionCalculatorOverridesForm(request.POST)
        overrides = {}
        if form.is_valid():
            for key in (
                "months_override",
                "school_days_override",
                "fee_agreement_override",
            ):
                if (val := form.cleaned_data.get(key)) is not None:
                    overrides[key] = val
        return self._render_calculator(supervision, form, **overrides)


class SupervisionBaseApplyView(BaseApplyView):
    title = "Betreuungsrechner"
    calculator_url_name = "admin:pedagogy_supervision_calculator"
    calculator_view_class = SupervisionCalculatorView

    def fetch_object(self, pk: int):
        try:
            return Supervision.objects.select_related(
                "student", "student__payer", "caretaker", "school", "tandem"
            ).get(pk=pk)
        except Supervision.DoesNotExist:
            raise Http404

    def run_calculation(self, obj: Supervision, overrides: dict):
        from .calculators import SupervisionCalculatorInput, run_supervision_calculation

        return run_supervision_calculation(
            SupervisionCalculatorInput(supervision=obj, **overrides)
        )


class SupervisionApplyTotalView(SupervisionBaseApplyView):
    def get_value(self, result):
        return result.calculated_total_amount

    def save_value(self, obj: Supervision, value) -> None:
        obj.total_amount = value
        obj.save(update_fields=["total_amount"])

    def error_message(self) -> str:
        return "Gesamtbetrag konnte nicht berechnet werden — keine Übernahme möglich."

    def success_message(self, formatted: str) -> str:
        return f"Gesamtbetrag übernommen: {formatted} €"


class SupervisionApplyInstallmentView(SupervisionBaseApplyView):
    def get_value(self, result):
        return result.calculated_monthly_installment

    def save_value(self, obj: Supervision, value) -> None:
        obj.monthly_installment = value
        obj.save(update_fields=["monthly_installment"])

    def error_message(self) -> str:
        return "Abschlag konnte nicht berechnet werden — keine Übernahme möglich."

    def success_message(self, formatted: str) -> str:
        return f"Abschlag übernommen: {formatted} €"


@admin.register(Student)
class StudentAdmin(BaseModelAdmin):
    list_display = ("full_name", "payer")
    search_fields = ("first_name", "last_name")
    inlines = [AddressInline, PhoneInline, EmailInline]
    autocomplete_fields = ("payer",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("payer")


@admin.register(Supervision)
class SupervisionAdmin(BaseModelAdmin):
    list_display = (
        "student",
        "tandem",
        "caretaker",
        "school",
        "start_date",
        "end_date",
        "weekly_hours",
        "is_prophylactic",
        "display_tandem_prophylactic",
        "display_total_amount",
    )
    actions_detail = ["edit_action", "calculator_action"]
    list_filter_submit = True
    list_filter = ("school", ("start_date", RangeDateFilter))
    search_fields = ("student__first_name", "student__last_name")
    autocomplete_fields = ("student", "tandem", "caretaker", "school")
    readonly_fields = ()
    conditional_fields = {"is_tandem_prophylactic": "!!tandem"}
    fieldsets = [
        ("Schüler:in", {"fields": [("student", "is_prophylactic")]}),
        ("Tandem", {"fields": [("tandem", "is_tandem_prophylactic")]}),
        ("Betreuung", {"fields": ["caretaker", ("school", "class_name")]}),
        ("Zeitraum", {"fields": [("start_date", "end_date"), "weekly_hours"]}),
        ("Abrechnung", {"fields": [("total_amount", "monthly_installment")]}),
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        return super().get_readonly_fields(request, obj)

    @action(
        description="Betreuungsrechner",
        url_path="calculator-action",
        permissions=["calculator_action"],
        variant=ActionVariant.DEFAULT,
    )
    def calculator_action(self, request, object_id: int):
        return redirect(
            reverse("admin:pedagogy_supervision_calculator", args=[object_id])
        )

    def has_calculator_action_permission(self, request, obj=None):
        return True

    @display(description="Tandem prophylaktisch", boolean=True)
    def display_tandem_prophylactic(self, obj: Supervision) -> bool | None:
        if not obj.tandem_id:
            return None
        return obj.is_tandem_prophylactic

    @display(description="Gesamtbetrag", ordering="total_amount")
    def display_total_amount(self, obj: Supervision) -> str:
        if obj.total_amount is not None:
            formatted = number_format(obj.total_amount, decimal_pos=2, use_l10n=True)
            return format_html("{} €", formatted)
        url = reverse("admin:pedagogy_supervision_calculator", args=[obj.pk])
        return format_html('<a href="{}">Berechnen →</a>', url)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "student", "student__payer", "caretaker", "school", "tandem"
            )
        )

    def get_urls(self):
        custom = [
            path(
                "<int:pk>/calculator/",
                self.admin_site.admin_view(
                    SupervisionCalculatorView.as_view(model_admin=self)
                ),
                name="pedagogy_supervision_calculator",
            ),
            path(
                "<int:pk>/calculator/apply-total/",
                self.admin_site.admin_view(
                    SupervisionApplyTotalView.as_view(model_admin=self)
                ),
                name="pedagogy_supervision_calculator_apply_total",
            ),
            path(
                "<int:pk>/calculator/apply-installment/",
                self.admin_site.admin_view(
                    SupervisionApplyInstallmentView.as_view(model_admin=self)
                ),
                name="pedagogy_supervision_calculator_apply_installment",
            ),
        ]
        return custom + super().get_urls()


@admin.register(Request)
class RequestAdmin(BaseModelAdmin):
    list_display = ("student", "state", "start_date", "demand", "review_date")
    list_filter = ("state",)
    search_fields = ("student__first_name", "student__last_name", "notes")
    autocomplete_fields = ("student", "school")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("student", "school")


@admin.register(School)
class SchoolAdmin(BaseModelAdmin):
    search_fields = ("name",)
