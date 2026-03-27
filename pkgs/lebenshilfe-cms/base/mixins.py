from django.contrib import admin
from django.urls import reverse
from django.http import HttpRequest
from django.shortcuts import redirect
from unfold.decorators import action
from unfold.enums import ActionVariant


class EditModeMixin:
    actions_detail = ["edit_action"]

    def _get_change_url(self, object_id: int) -> str:
        return reverse(
            f"admin:{self.opts.app_label}_{self.opts.model_name}_change",
            args=[object_id],
        )

    @action(
        description="Bearbeiten",
        url_path="edit-action",
        permissions=["edit_action"],
        variant=ActionVariant.PRIMARY,
    )
    def edit_action(self, request: HttpRequest, object_id: int):
        url = self._get_change_url(object_id)
        return redirect(f"{url}?edit=1")

    def has_edit_action_permission(self, request, obj=None):
        return not self.is_edit(request)

    def is_edit(self, request):
        return request.GET.get("edit") == "1"

    def has_change_permission(self, request, obj=None):
        has_class_permission = super().has_change_permission(request, obj)
        if not has_class_permission:
            return False
        return self.is_edit(request)


class AdminDisplayMixin:
    @staticmethod
    def duration_display(field_name, description="Dauer"):
        @admin.display(description=description, ordering=field_name)
        def display_fn(self, obj):
            value = getattr(obj, field_name)
            if value:
                total_seconds = int(value.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return f"{hours}:{minutes:02d} Std."
            return "-"

        return display_fn
