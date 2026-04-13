from datetime import date
from urllib.parse import urlencode

from django.contrib import messages
from django import forms
from django.core.paginator import EmptyPage, InvalidPage, Paginator
from django.db.models import QuerySet
from django.http import Http404, HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.formats import number_format
from django.views.generic import TemplateView, View
from unfold.views import UnfoldModelAdminViewMixin


class BaseCalculatorView(UnfoldModelAdminViewMixin, TemplateView):
    title = "Rechner"
    template_name = "admin/calculator_base.html"
    permission_required = []
    form_class = None

    def get_queryset(self):
        return self.model_admin.get_queryset(self.request)

    def get_object(self):
        pk = self.kwargs.get("pk")
        try:
            return self.get_queryset().get(pk=pk)
        except self.model_admin.model.DoesNotExist:
            raise Http404

    def run_calculation(self, obj, overrides: dict):
        raise NotImplementedError

    def parse_overrides(self, request_data) -> dict:
        form_class = self.get_form_class()
        overrides = {}
        if form_class and request_data:
            form = form_class(request_data)
            if form.is_valid():
                for key, val in form.cleaned_data.items():
                    if val is not None:
                        overrides[key] = val
        return overrides

    def overrides_to_params(self, overrides: dict) -> dict:
        params = {}
        for key, val in overrides.items():
            if val is None:
                continue
            if hasattr(val, "pk"):
                params[key] = str(val.pk)
            else:
                params[key] = str(val)
        return params

    def get_source_fields(self, obj):
        return []

    def get_primary_results(self, obj, result):
        return []

    def get_result_rows(self, obj, result):
        return []

    def get_warnings(self, result):
        return getattr(result, "warnings", [])

    def build_apply_url(self, obj, url_name, override_params):
        url = reverse(url_name, args=[obj.pk])
        if override_params:
            url += "?" + urlencode(override_params)
        return url

    def get_breadcrumb_items(self, obj):
        opts = self.model_admin.model._meta
        return [
            {
                "label": opts.app_config.verbose_name,
                "url": reverse("admin:app_list", kwargs={"app_label": opts.app_label}),
            },
            {
                "label": str(opts.verbose_name_plural).capitalize(),
                "url": reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist"),
            },
            {
                "label": str(obj),
                "url": reverse(
                    f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk]
                ),
            },
            {"label": self.title, "url": None},
        ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obj = kwargs.get("obj") or self.get_object()
        result = kwargs.get("result")
        form = kwargs.get("form")

        opts = self.model_admin.model._meta

        ctx.update(
            {
                "title": self.title,
                "source_fields": self.get_source_fields(obj),
                "primary_results": self.get_primary_results(obj, result),
                "result_rows": self.get_result_rows(obj, result),
                "warnings": self.get_warnings(result),
                "breadcrumb_items": self.get_breadcrumb_items(obj),
                "opts": opts,
                "form": form,
                "media": self.model_admin.media
                + (form.media if form else forms.Media())
                + forms.Media(js=[reverse("javascript-catalog")]),
                "change_url": reverse(
                    f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk]
                ),
            }
        )
        return ctx

    def _render_calculator(self, obj, form, overrides):
        result = self.run_calculation(obj, overrides)
        return self.render_to_response(
            self.get_context_data(obj=obj, result=result, form=form)
        )

    def get_form_class(self):
        return self.form_class

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        overrides = self.parse_overrides(request.GET)
        form_class = self.get_form_class()
        form = form_class(initial=overrides or None) if form_class else None
        return self._render_calculator(obj, form, overrides)

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        overrides = self.parse_overrides(request.POST)
        form_class = self.get_form_class()
        form = form_class(request.POST) if form_class else None
        return self._render_calculator(obj, form, overrides)


class BaseApplyView(UnfoldModelAdminViewMixin, View):
    """Basisklasse für Apply-Views nach dem Template-Method-Pattern.

    Subklassen müssen setzen:
      - title, calculator_url_name, calculator_view_class

    Subklassen müssen implementieren:
      - get_value, save_value, error_message, success_message
    """

    title: str = ""
    permission_required = []
    calculator_url_name: str = ""
    calculator_view_class: type[BaseCalculatorView]

    def get_queryset(self):
        return self.model_admin.get_queryset(self.request)

    def get_object(self):
        pk = self.kwargs.get("pk")
        try:
            return self.get_queryset().get(pk=pk)
        except self.model_admin.model.DoesNotExist:
            raise Http404

    def get_redirect_url(self, pk: int, overrides: dict | None = None) -> str:
        url = reverse(self.calculator_url_name, args=[pk])
        if overrides:
            url += "?" + urlencode(overrides)
        return url

    def get(self, request, *args, **kwargs):
        return redirect(self.get_redirect_url(self.kwargs["pk"]))

    def get_value(self, result):
        raise NotImplementedError

    def save_value(self, obj, value) -> None:
        raise NotImplementedError

    def error_message(self) -> str:
        raise NotImplementedError

    def success_message(self, formatted: str) -> str:
        raise NotImplementedError

    def post(self, request, *args, **kwargs):
        pk = self.kwargs["pk"]
        calc_view = self.calculator_view_class(model_admin=self.model_admin)
        overrides = calc_view.parse_overrides(request.GET)
        obj = self.get_object()
        result = calc_view.run_calculation(obj, overrides)
        value = self.get_value(result)
        if value is None:
            messages.error(request, self.error_message())
        else:
            self.save_value(obj, value)
            formatted = number_format(value, decimal_pos=2, use_l10n=True)
            messages.success(request, self.success_message(formatted))
        params = calc_view.overrides_to_params(overrides)
        return redirect(self.get_redirect_url(pk, params))


# ---------------------------------------------------------------------------
# Union-Listen-Views
# ---------------------------------------------------------------------------


class UnionListMixin:
    """Mixin für Union-Listen-Views aus zwei QuerySets mit Form-Filtern und Paginierung."""

    union_ordering: str = "-start_date"
    per_page: int = 50

    # Standard Unfold Badge Styles
    LABEL_INFO = (
        "inline-block font-semibold rounded-default text-[11px] uppercase "
        "whitespace-nowrap h-5 leading-5 px-1.5 "
        "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400"
    )
    LABEL_SUCCESS = (
        "inline-block font-semibold rounded-default text-[11px] uppercase "
        "whitespace-nowrap h-5 leading-5 px-1.5 "
        "bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-400"
    )
    LABEL_WARNING = (
        "inline-block font-semibold rounded-default text-[11px] uppercase "
        "whitespace-nowrap h-5 leading-5 px-1.5 "
        "bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-400"
    )
    LABEL_DANGER = (
        "inline-block font-semibold rounded-default text-[11px] uppercase "
        "whitespace-nowrap h-5 leading-5 px-1.5 "
        "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400"
    )

    def get_queryset_a(self, request: HttpRequest) -> QuerySet:
        raise NotImplementedError

    def get_queryset_b(self, request: HttpRequest) -> QuerySet:
        raise NotImplementedError

    def get_columns(self) -> list[str]:
        raise NotImplementedError

    def get_row(self, obj) -> list:
        raise NotImplementedError

    def get_filter_form_class(self):
        """Gibt die Filter-Formularklasse zurück. Optional — Subklassen überschreiben."""
        return None

    def get_breadcrumb_items(self) -> list[dict]:
        opts = self.model_admin.model._meta
        return [
            {
                "label": opts.app_config.verbose_name,
                "url": reverse("admin:app_list", kwargs={"app_label": opts.app_label}),
            },
            {"label": self.title, "url": None},
        ]

    def _apply_filter_form(self, qs: QuerySet, form) -> QuerySet:
        """Wendet das Filter-Formular auf ein QuerySet an."""
        if form is not None:
            return form.filter_queryset(qs)
        return qs

    def _sort_key(self, obj):
        field = self.union_ordering.lstrip("-")
        return getattr(obj, field, None) or date.min

    def _merged_and_filtered(self, request: HttpRequest, form) -> list:
        qs_a = self._apply_filter_form(self.get_queryset_a(request), form)
        qs_b = self._apply_filter_form(self.get_queryset_b(request), form)
        merged = list(qs_a) + list(qs_b)
        merged.sort(key=self._sort_key, reverse=self.union_ordering.startswith("-"))
        return merged

    def _build_table(self, page_objects) -> dict:
        return {
            "headers": self.get_columns(),
            "rows": [{"cols": self.get_row(obj)} for obj in page_objects],
            "striped": 1,
        }

    def _has_active_filters(self, form) -> bool:
        """Prüft ob der Nutzer aktive Filterparameter gesetzt hat."""
        if form is None:
            return False
        return any(self.request.GET.get(field_name) for field_name in form.fields)

    def get_context_data(self, **kwargs) -> dict:
        ctx = super().get_context_data(**kwargs)
        request = self.request

        filter_form_class = self.get_filter_form_class()
        filter_form = (
            filter_form_class(request.GET or None) if filter_form_class else None
        )

        merged = self._merged_and_filtered(request, filter_form)

        paginator = Paginator(merged, self.per_page)
        try:
            page_num = int(request.GET.get("p", 1))
        except (ValueError, TypeError):
            page_num = 1
        try:
            page_obj = paginator.page(page_num)
        except (EmptyPage, InvalidPage):
            page_obj = paginator.page(paginator.num_pages)

        # Build query string base (all current GET params except 'p')
        params = request.GET.copy()
        params.pop("p", None)
        query_string_base = params.urlencode()

        ctx.update(
            {
                "title": self.title,
                "page_obj": page_obj,
                "paginator": paginator,
                "query_string_base": query_string_base,
                "filter_form": filter_form,
                "has_active_filters": self._has_active_filters(filter_form),
                "table": self._build_table(page_obj.object_list),
                "breadcrumb_items": self.get_breadcrumb_items(),
                "opts": self.model_admin.model._meta,
                "media": self.model_admin.media
                + (filter_form.media if filter_form else forms.Media())
                + forms.Media(js=[reverse("javascript-catalog")]),
                "page_range": paginator.get_elided_page_range(page_obj.number),
                "pagination_required": paginator.num_pages > 1,
            }
        )
        return ctx


class BaseUnionListView(UnionListMixin, UnfoldModelAdminViewMixin, TemplateView):
    """Basisklasse für Union-Listen-Views aus zwei QuerySets.

    Analog zu BaseCalculatorView — wird mit model_admin als View-Parameter
    instantiiert und in get_urls() einer ModelAdmin-Klasse registriert.
    """

    template_name = "admin/union_list_base.html"
    permission_required = []
    title = "Übersicht"

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data())
