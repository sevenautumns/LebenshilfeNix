from urllib.parse import urlencode

from django.contrib import admin, messages
from django.http import Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.formats import number_format
from django.utils.html import format_html
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import action, display
from unfold.enums import ActionVariant

from base.admin import BaseModelAdmin, AddressInline, PhoneInline, EmailInline
from base.fields import EuroDecimalField

from .models import School, Student, Supervision, Request

_euro_fmt = EuroDecimalField(max_digits=10, decimal_places=2)


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
    readonly_fields = ("total_amount", "monthly_installment")
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
                self.admin_site.admin_view(self.calculator_view),
                name="pedagogy_supervision_calculator",
            ),
            path(
                "<int:pk>/calculator/apply-total/",
                self.admin_site.admin_view(self.apply_total_view),
                name="pedagogy_supervision_calculator_apply_total",
            ),
            path(
                "<int:pk>/calculator/apply-installment/",
                self.admin_site.admin_view(self.apply_installment_view),
                name="pedagogy_supervision_calculator_apply_installment",
            ),
        ]
        return custom + super().get_urls()

    def _get_supervision(self, pk: int) -> Supervision:
        try:
            return Supervision.objects.select_related(
                "student", "student__payer", "caretaker", "school", "tandem"
            ).get(pk=pk)
        except Supervision.DoesNotExist:
            raise Http404

    def _override_params(
        self, months_override, school_days_override, fee_agreement_override
    ) -> dict:
        params = {}
        if months_override is not None:
            params["months_override"] = str(months_override)
        if school_days_override is not None:
            params["school_days_override"] = str(school_days_override)
        if fee_agreement_override is not None:
            params["fee_agreement_override"] = str(fee_agreement_override.pk)
        return params

    def _build_redirect_url(self, url_name: str, pk: int, params: dict) -> str:
        url = reverse(url_name, args=[pk])
        if params:
            url += "?" + urlencode(params)
        return url

    def _parse_overrides(self, data: dict):
        """Liest Override-Werte aus GET-Params oder POST-Daten."""
        from decimal import Decimal
        from finance.models import FeeAgreement

        months_override = None
        school_days_override = None
        fee_agreement_override = None

        if mo := data.get("months_override"):
            try:
                months_override = Decimal(mo)
            except Exception:
                pass
        if sd := data.get("school_days_override"):
            try:
                school_days_override = int(sd)
            except Exception:
                pass
        if fev_pk := data.get("fee_agreement_override"):
            try:
                fee_agreement_override = FeeAgreement.objects.get(pk=int(fev_pk))
            except Exception:
                pass

        return months_override, school_days_override, fee_agreement_override

    def calculator_view(self, request, pk: int):
        from base.fields import HourMinuteDurationField as HMField

        from .calculators import SupervisionCalculatorInput, run_supervision_calculation
        from .forms import SupervisionCalculatorOverridesForm

        supervision = self._get_supervision(pk)

        months_override = None
        school_days_override = None
        fee_agreement_override = None

        if request.method == "POST":
            form = SupervisionCalculatorOverridesForm(request.POST)
            if form.is_valid():
                months_override = form.cleaned_data.get("months_override")
                school_days_override = form.cleaned_data.get("school_days_override")
                fee_agreement_override = form.cleaned_data.get("fee_agreement_override")
        else:
            months_override, school_days_override, fee_agreement_override = (
                self._parse_overrides(request.GET)
            )
            initial = {}
            if months_override is not None:
                initial["months_override"] = months_override
            if school_days_override is not None:
                initial["school_days_override"] = school_days_override
            if fee_agreement_override is not None:
                initial["fee_agreement_override"] = fee_agreement_override
            form = SupervisionCalculatorOverridesForm(initial=initial or None)

        result = run_supervision_calculation(
            SupervisionCalculatorInput(
                supervision=supervision,
                months_override=months_override,
                school_days_override=school_days_override,
                fee_agreement_override=fee_agreement_override,
            )
        )

        opts = self.model._meta
        override_params = self._override_params(
            months_override, school_days_override, fee_agreement_override
        )
        apply_total_url = self._build_redirect_url(
            "admin:pedagogy_supervision_calculator_apply_total", pk, override_params
        )
        apply_installment_url = self._build_redirect_url(
            "admin:pedagogy_supervision_calculator_apply_installment",
            pk,
            override_params,
        )

        source_fields = [
            ("Schüler:in", str(supervision.student)),
            (
                "Kostenträger",
                str(supervision.student.payer) if supervision.student_id else "—",
            ),
            ("Schule", str(supervision.school)),
            (
                "Zeitraum",
                f"{supervision.start_date.strftime('%d.%m.%Y')} – {supervision.end_date.strftime('%d.%m.%Y')}",
            ),
            (
                "Wochenstunden",
                HMField.format_std(supervision.weekly_hours),
            ),
            ("Schultage (rechnerisch)", supervision.calculated_school_days),
        ]

        primary_results = [
            {
                "label": "Gesamtbetrag (berechnet)",
                "value": result.calculated_total_amount,
                "unit": "€",
                "stored_label": "Aktuell gespeichert",
                "stored_value": supervision.total_amount,
                "apply_url": apply_total_url
                if result.calculated_total_amount is not None
                else None,
            },
            {
                "label": "Abschlag pro Monat (berechnet)",
                "value": result.calculated_monthly_installment,
                "unit": "€",
                "stored_label": "Aktuell gespeichert",
                "stored_value": supervision.monthly_installment,
                "apply_url": apply_installment_url
                if result.calculated_monthly_installment is not None
                else None,
            },
        ]

        result_rows = []
        if result.is_pool_rate and result.pool_agreement:
            result_rows.append(("Abrechnungsart", "Pauschale (Poolvereinbarung)", True))
            result_rows.append(("Poolvereinbarung", str(result.pool_agreement), False))
        else:
            result_rows.append(
                (
                    "Entgeltvereinbarung",
                    str(result.fee_agreement) if result.fee_agreement else "—",
                    fee_agreement_override is not None,
                )
            )
        result_rows += [
            (
                "Schultage (effektiv)",
                result.school_days,
                school_days_override is not None,
            ),
            ("Monate (rechnerisch)", supervision.calculated_months, False),
            (
                "Effektive Monate",
                result.months,
                result.months != supervision.calculated_months,
            ),
        ]

        breadcrumb_items = [
            {
                "label": opts.app_config.verbose_name,
                "url": reverse("admin:app_list", kwargs={"app_label": opts.app_label}),
            },
            {
                "label": str(opts.verbose_name_plural).capitalize(),
                "url": reverse("admin:pedagogy_supervision_changelist"),
            },
            {
                "label": str(supervision),
                "url": reverse(
                    "admin:pedagogy_supervision_change", args=[supervision.pk]
                ),
            },
            {"label": "Betreuungsrechner", "url": None},
        ]

        context = self.admin_site.each_context(request)
        context |= {
            "title": "Betreuungsrechner",
            "supervision": supervision,
            "form": form,
            "source_fields": source_fields,
            "primary_results": primary_results,
            "result_rows": result_rows,
            "warnings": result.warnings,
            "breadcrumb_items": breadcrumb_items,
            "opts": opts,
            "media": self.media + form.media,
        }
        return TemplateResponse(request, "admin/calculator_base.html", context)

    def _run_calc_from_request(self, supervision: Supervision, request):
        from .calculators import SupervisionCalculatorInput, run_supervision_calculation

        months_override, school_days_override, fee_agreement_override = (
            self._parse_overrides(request.GET)
        )
        return (
            run_supervision_calculation(
                SupervisionCalculatorInput(
                    supervision=supervision,
                    months_override=months_override,
                    school_days_override=school_days_override,
                    fee_agreement_override=fee_agreement_override,
                )
            ),
            months_override,
            school_days_override,
            fee_agreement_override,
        )

    def apply_total_view(self, request, pk: int):
        if request.method != "POST":
            return redirect(reverse("admin:pedagogy_supervision_calculator", args=[pk]))

        supervision = self._get_supervision(pk)
        result, months_override, school_days_override, fee_agreement_override = (
            self._run_calc_from_request(supervision, request)
        )

        if result.calculated_total_amount is None:
            messages.error(
                request,
                "Gesamtbetrag konnte nicht berechnet werden — keine Übernahme möglich.",
            )
        else:
            supervision.total_amount = result.calculated_total_amount
            supervision.save(update_fields=["total_amount"])
            formatted = number_format(
                result.calculated_total_amount, decimal_pos=2, use_l10n=True
            )
            messages.success(request, f"Gesamtbetrag übernommen: {formatted} €")

        params = self._override_params(
            months_override, school_days_override, fee_agreement_override
        )
        return redirect(
            self._build_redirect_url(
                "admin:pedagogy_supervision_calculator", pk, params
            )
        )

    def apply_installment_view(self, request, pk: int):
        if request.method != "POST":
            return redirect(reverse("admin:pedagogy_supervision_calculator", args=[pk]))

        supervision = self._get_supervision(pk)
        result, months_override, school_days_override, fee_agreement_override = (
            self._run_calc_from_request(supervision, request)
        )

        if result.calculated_monthly_installment is None:
            messages.error(
                request,
                "Abschlag konnte nicht berechnet werden — keine Übernahme möglich.",
            )
        else:
            supervision.monthly_installment = result.calculated_monthly_installment
            supervision.save(update_fields=["monthly_installment"])
            formatted = number_format(
                result.calculated_monthly_installment, decimal_pos=2, use_l10n=True
            )
            messages.success(request, f"Abschlag übernommen: {formatted} €")

        params = self._override_params(
            months_override, school_days_override, fee_agreement_override
        )
        return redirect(
            self._build_redirect_url(
                "admin:pedagogy_supervision_calculator", pk, params
            )
        )


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
