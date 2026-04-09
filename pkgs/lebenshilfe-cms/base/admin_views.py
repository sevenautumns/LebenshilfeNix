from urllib.parse import urlencode

from django.contrib import messages
from django import forms
from django.http import Http404
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
        return self.model_admin.model.objects.all()

    def get_object(self):
        pk = self.kwargs.get("pk")
        try:
            return self.get_queryset().get(pk=pk)
        except self.model_admin.model.DoesNotExist:
            raise Http404

    def run_calculation(self, obj, overrides: dict):
        raise NotImplementedError

    def get_source_fields(self, obj):
        return []

    def get_primary_results(self, obj, result):
        return []

    def get_result_rows(self, obj, result):
        return []

    def get_warnings(self, result):
        return getattr(result, "warnings", [])

    @classmethod
    def parse_overrides(cls, data: dict) -> dict:
        """Parst Override-Werte aus GET/POST-Daten. In Subklassen überschreiben."""
        return {}

    @classmethod
    def overrides_to_params(cls, overrides: dict) -> dict:
        """Serialisiert Override-Werte zu URL-Query-Params. In Subklassen überschreiben."""
        return {}

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
                + (form.media if form else forms.Media()),
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

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        overrides = self.parse_overrides(request.GET)
        form = self.form_class(initial=overrides or None) if self.form_class else None
        return self._render_calculator(obj, form, overrides)

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        form = self.form_class(request.POST) if self.form_class else None
        overrides = {}
        if form and form.is_valid():
            for key, val in form.cleaned_data.items():
                if val is not None:
                    overrides[key] = val
        return self._render_calculator(obj, form, overrides)


class BaseApplyView(UnfoldModelAdminViewMixin, View):
    """Basisklasse für Apply-Views nach dem Template-Method-Pattern.

    Subklassen müssen setzen:
      - title, calculator_url_name, calculator_view_class

    Subklassen müssen implementieren:
      - run_calculation, get_value, save_value,
        error_message, success_message
    """

    title: str = ""
    permission_required = []
    calculator_url_name: str = ""
    calculator_view_class: type[BaseCalculatorView]

    def get_queryset(self):
        return self.model_admin.model.objects.all()

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

    def run_calculation(self, obj, overrides: dict):
        raise NotImplementedError

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
        overrides = self.calculator_view_class.parse_overrides(request.GET)
        obj = self.get_object()
        result = self.run_calculation(obj, overrides)
        value = self.get_value(result)
        if value is None:
            messages.error(request, self.error_message())
        else:
            self.save_value(obj, value)
            formatted = number_format(value, decimal_pos=2, use_l10n=True)
            messages.success(request, self.success_message(formatted))
        params = self.calculator_view_class.overrides_to_params(overrides)
        return redirect(self.get_redirect_url(pk, params))
