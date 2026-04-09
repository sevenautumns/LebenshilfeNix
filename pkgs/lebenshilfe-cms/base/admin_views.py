from django.urls import reverse
from django.views.generic import TemplateView
from unfold.views import UnfoldModelAdminViewMixin
from django.http import Http404


class BaseCalculatorView(UnfoldModelAdminViewMixin, TemplateView):
    title = "Rechner"
    template_name = "admin/calculator_base.html"
    permission_required = []

    def get_queryset(self):
        return self.model_admin.model.objects.all()

    def get_object(self):
        pk = self.kwargs.get("pk")
        try:
            return self.get_queryset().get(pk=pk)
        except self.model_admin.model.DoesNotExist:
            raise Http404

    def get_source_fields(self, obj):
        return []

    def get_primary_results(self, obj, result):
        return []

    def get_result_rows(self, obj, result):
        return []

    def get_warnings(self, result):
        return getattr(result, "warnings", [])

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
                "media": self.model_admin.media + (form.media if form else ""),
                "change_url": reverse(
                    f"admin:{opts.app_label}_{opts.model_name}_change", args=[obj.pk]
                ),
            }
        )
        return ctx
