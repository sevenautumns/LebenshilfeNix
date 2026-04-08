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
from base.fields import HourMinuteDurationField, EuroDecimalField

from .models import School, Student, Supervision, Request

_duration_fmt = HourMinuteDurationField()
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
    readonly_fields = (
        "calculated_school_days",
        "calculated_months",
        "display_daily_hours",
        "display_yearly_hours",
        "display_monthly_hours",
        "fee_agreement",
    )
    conditional_fields = {"is_tandem_prophylactic": "!!tandem"}
    fieldsets = [
        ("Schüler:in", {"fields": [("student", "is_prophylactic")]}),
        ("Tandem", {"fields": [("tandem", "is_tandem_prophylactic")]}),
        ("Betreuung", {"fields": ["caretaker", ("school", "class_name")]}),
        (
            "Zeitraum & Stunden",
            {
                "fields": [
                    ("start_date", "end_date"),
                    ("weekly_hours", "display_daily_hours"),
                    ("calculated_school_days", "school_days_override"),
                    ("calculated_months", "months_override"),
                    ("display_yearly_hours", "display_monthly_hours"),
                ]
            },
        ),
        (
            "Abrechnung",
            {
                "fields": [
                    "fee_agreement",
                    ("total_amount", "monthly_installment"),
                ]
            },
        ),
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

    @display(description="Stunden pro Tag")
    def display_daily_hours(self, obj: Supervision) -> str:
        return _duration_fmt.get_admin_format(obj.daily_hours)

    @display(description="Jahresstunden")
    def display_yearly_hours(self, obj: Supervision) -> str:
        return _duration_fmt.get_admin_format(obj.yearly_hours)

    @display(description="Monatsstunden")
    def display_monthly_hours(self, obj: Supervision) -> str:
        from datetime import timedelta

        if obj.monthly_hours is None:
            return "—"
        return _duration_fmt.get_admin_format(timedelta(hours=float(obj.monthly_hours)))

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

    def _build_apply_url(self, url_name: str, pk: int, months_override) -> str:
        url = reverse(url_name, args=[pk])
        if months_override is not None:
            url += "?" + urlencode({"months_override": str(months_override)})
        return url

    def calculator_view(self, request, pk: int):
        from decimal import Decimal

        from base.fields import HourMinuteDurationField as HMField

        from .calculators import SupervisionCalculatorInput, run_supervision_calculation
        from .forms import SupervisionCalculatorOverridesForm

        supervision = self._get_supervision(pk)

        months_override = None
        if request.method == "POST":
            form = SupervisionCalculatorOverridesForm(request.POST)
            if form.is_valid():
                months_override = form.cleaned_data.get("months_override")
        else:
            # Pre-populate from query params (preserved after apply redirect)
            initial = {}
            if mo := request.GET.get("months_override"):
                try:
                    months_override = Decimal(mo)
                    initial["months_override"] = months_override
                except Exception:
                    pass
            form = SupervisionCalculatorOverridesForm(initial=initial or None)

        result = run_supervision_calculation(
            SupervisionCalculatorInput(
                supervision=supervision,
                months_override=months_override,
            )
        )

        opts = self.model._meta
        apply_total_url = self._build_apply_url(
            "admin:pedagogy_supervision_calculator_apply_total", pk, months_override
        )
        apply_installment_url = self._build_apply_url(
            "admin:pedagogy_supervision_calculator_apply_installment",
            pk,
            months_override,
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
                    False,
                )
            )
        result_rows += [
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

    def apply_total_view(self, request, pk: int):
        if request.method != "POST":
            return redirect(reverse("admin:pedagogy_supervision_calculator", args=[pk]))

        from decimal import Decimal

        from .calculators import SupervisionCalculatorInput, run_supervision_calculation

        supervision = self._get_supervision(pk)
        months_override_str = request.GET.get("months_override")
        months_override = None
        if months_override_str:
            try:
                months_override = Decimal(months_override_str)
            except Exception:
                pass

        result = run_supervision_calculation(
            SupervisionCalculatorInput(
                supervision=supervision,
                months_override=months_override,
            )
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

        redirect_url = reverse("admin:pedagogy_supervision_calculator", args=[pk])
        if months_override is not None:
            redirect_url += "?" + urlencode({"months_override": str(months_override)})
        return redirect(redirect_url)

    def apply_installment_view(self, request, pk: int):
        if request.method != "POST":
            return redirect(reverse("admin:pedagogy_supervision_calculator", args=[pk]))

        from decimal import Decimal

        from .calculators import SupervisionCalculatorInput, run_supervision_calculation

        supervision = self._get_supervision(pk)
        months_override_str = request.GET.get("months_override")
        months_override = None
        if months_override_str:
            try:
                months_override = Decimal(months_override_str)
            except Exception:
                pass

        result = run_supervision_calculation(
            SupervisionCalculatorInput(
                supervision=supervision,
                months_override=months_override,
            )
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

        redirect_url = reverse("admin:pedagogy_supervision_calculator", args=[pk])
        if months_override is not None:
            redirect_url += "?" + urlencode({"months_override": str(months_override)})
        return redirect(redirect_url)


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
