from django.urls import reverse
from django.http import HttpRequest
from django.shortcuts import redirect
from unfold.decorators import action
from unfold.enums import ActionVariant
import types


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
        if obj is None:
            return has_class_permission
        return self.is_edit(request)


class AdminDisplayMixin:
    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)

        for field in self.opts.fields:
            method_name = f"display_{field.name}"

            if hasattr(self, method_name):
                continue

            if hasattr(field, "get_admin_format"):
                func = self._generate_generic_display(field)
                setattr(self, method_name, types.MethodType(func, self))

    def _generate_generic_display(self, field):
        def display_fn(self_instance, obj):
            value = getattr(obj, field.name)
            return field.get_admin_format(value)

        display_fn.short_description = field.verbose_name
        display_fn.admin_order_field = field.name
        return display_fn

    def get_readonly_fields(self, request, obj=None):
        ro_fields = list(super().get_readonly_fields(request, obj))
        if obj is not None and not self.has_change_permission(request, obj):
            for field in self.opts.fields:
                display_name = f"display_{field.name}"
                if hasattr(self, display_name):
                    if field.name in ro_fields:
                        ro_fields[ro_fields.index(field.name)] = display_name
                    elif display_name not in ro_fields:
                        ro_fields.append(display_name)
        return ro_fields

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if obj is not None and not self.has_change_permission(request, obj):
            for field in self.opts.fields:
                display_name = f"display_{field.name}"
                if hasattr(self, display_name) and field.name in fields:
                    idx = fields.index(field.name)
                    fields[idx] = display_name
        return fields

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))
        new_list_display = []
        for item in list_display:
            if isinstance(item, str) and hasattr(self, f"display_{item}"):
                new_list_display.append(f"display_{item}")
            else:
                new_list_display.append(item)
        return new_list_display
