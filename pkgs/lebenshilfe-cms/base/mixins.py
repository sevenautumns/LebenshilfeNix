from __future__ import annotations

from decimal import Decimal

from django import forms
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from unfold.decorators import action, display
from unfold.enums import ActionVariant
import types

from base.calculated_fields.types import CalculationEntry


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
        @display(description=field.verbose_name, ordering=field.name)
        def display_fn(self_instance, obj):
            value = getattr(obj, field.name)
            return field.get_admin_format(value)

        return display_fn

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        # On add: fields listed in readonly_fields have no widget → strip them
        strip = set(self.readonly_fields) if obj is None else set()

        # In view mode: swap field_name → display_field_name (same as get_fields does)
        replacements = {}
        if obj is not None and not self.has_change_permission(request, obj):
            replacements = {
                field.name: f"display_{field.name}"
                for field in self.opts.fields
                if hasattr(self, f"display_{field.name}")
            }

        if not strip and not replacements:
            return fieldsets

        new_fieldsets = []
        for section_name, options in fieldsets:
            new_fields = []
            for row in options.get("fields", []):
                if isinstance(row, (list, tuple)):
                    new_row = [replacements.get(f, f) for f in row if f not in strip]
                    if len(new_row) == 1:
                        new_fields.append(new_row[0])
                    elif len(new_row) > 1:
                        new_fields.append(tuple(new_row))
                else:
                    if row not in strip:
                        new_fields.append(replacements.get(row, row))
            if new_fields:
                new_fieldsets.append((section_name, {**options, "fields": new_fields}))
        return new_fieldsets

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if obj is not None and not self.has_change_permission(request, obj):
            replacements = {
                field.name: f"display_{field.name}"
                for field in self.opts.fields
                if hasattr(self, f"display_{field.name}")
            }
            mapped_fields = [replacements.get(field, field) for field in fields]
            return list(dict.fromkeys(mapped_fields))
        return fields

    def get_readonly_fields(self, request, obj=None):
        ro_fields = list(super().get_readonly_fields(request, obj))
        if obj is not None and not self.has_change_permission(request, obj):
            replacements = {
                field.name: f"display_{field.name}"
                for field in self.opts.fields
                if hasattr(self, f"display_{field.name}")
            }
            mapped_ro_fields = [replacements.get(field, field) for field in ro_fields]
            mapped_ro_fields.extend(replacements.values())
            return list(dict.fromkeys(mapped_ro_fields))
        return ro_fields

    def get_list_display(self, request):
        list_display = list(super().get_list_display(request))
        new_list_display = []
        for item in list_display:
            if isinstance(item, str) and hasattr(self, f"display_{item}"):
                new_list_display.append(f"display_{item}")
            else:
                new_list_display.append(item)
        return new_list_display


class CalculatedFieldsMixin:
    """
    Generic mixin for ModelAdmin whose model has a ``calculations`` property
    returning ``dict[str, CalculationEntry]``.

    The model must also expose:
    - ``get_calculation_schema()`` classmethod → same dict shape with ``value=None``
    - ``overrides`` JSONField (default=dict)
    - ``gross_salary_contract`` field (the one stored result)
    - ``version`` field

    Behaviour:
    - View mode: each entry rendered as a readonly ``display_calc_<key>`` method.
    - Edit mode: overridable entries get an editable input alongside the display.
    - On save: override values are written back to ``obj.overrides``; the effective
      gross salary is written to ``obj.gross_salary_contract``.
    """

    calculations_fieldset_name: str = "Vergütung"

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self._register_calc_display_methods()

    # ------------------------------------------------------------------
    # Schema helpers
    # ------------------------------------------------------------------

    def _get_default_schema(self) -> dict[str, CalculationEntry]:
        """Return the field schema without a real instance (for method registration)."""
        if hasattr(self.model, "get_calculation_schema"):
            return self.model.get_calculation_schema()
        return {}

    def _register_calc_display_methods(self) -> None:
        """Dynamically attach display_calc_<key>() methods based on the schema."""
        schema = self._get_default_schema()
        for key, entry in schema.items():
            method_name = f"display_calc_{key}"
            if hasattr(self, method_name):
                continue
            func = self._make_calc_display_fn(key, entry["label"])
            setattr(self, method_name, types.MethodType(func, self))

    def _make_calc_display_fn(self, key: str, label: str):
        @display(description=label)
        def display_fn(self_instance, obj):
            calcs = obj.calculations
            entry = calcs.get(key, {})
            return self_instance._format_calc_value(entry)

        return display_fn

    def _format_calc_value(self, entry: CalculationEntry) -> str:
        from base.fields import EuroDecimalField

        _euro_fmt = EuroDecimalField(max_digits=10, decimal_places=2)
        value = entry.get("value")
        field_type = entry.get("field_type", "text")
        if value is None:
            return "—"
        if field_type == "euro":
            return _euro_fmt.get_admin_format(value)
        return str(value)

    # ------------------------------------------------------------------
    # Admin overrides
    # ------------------------------------------------------------------

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        for key in self._get_default_schema():
            method_name = f"display_calc_{key}"
            if method_name not in ro:
                ro.append(method_name)
        return ro

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        if obj is None:
            # On add: strip the calculations section entirely
            return [
                (name, opts)
                for name, opts in fieldsets
                if name != self.calculations_fieldset_name
            ]

        calcs = obj.calculations
        in_edit = self.is_edit(request)

        calc_fields = []
        for key, entry in calcs.items():
            display_name = f"display_calc_{key}"
            if in_edit and entry["overridable"] and entry["override_key"]:
                calc_fields.append((display_name, f"override_{entry['override_key']}"))
            else:
                calc_fields.append(display_name)

        new_fieldsets = []
        for name, opts in fieldsets:
            if name == self.calculations_fieldset_name:
                new_fieldsets.append((name, {**opts, "fields": calc_fields}))
            else:
                new_fieldsets.append((name, opts))
        return new_fieldsets

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change=change, **kwargs)
        if not self.is_edit(request) or obj is None:
            return form

        calcs = obj.calculations
        overrides = obj.overrides or {}
        extra_fields: dict[str, forms.Field] = {}

        for key, entry in calcs.items():
            if not entry["overridable"] or not entry["override_key"]:
                continue
            override_key = entry["override_key"]
            initial_raw = overrides.get(override_key)
            initial = None
            if initial_raw is not None:
                try:
                    initial = Decimal(str(initial_raw))
                except Exception:
                    pass
            extra_fields[f"override_{override_key}"] = self._make_override_form_field(
                entry["field_type"], entry["label"], initial
            )

        if not extra_fields:
            return form

        return type(form.__name__, (form,), extra_fields)

    def _make_override_form_field(
        self, field_type: str, label: str, initial: Decimal | int | None
    ) -> forms.Field:
        from base.widgets import EuroDecimalWidget

        common: dict = {
            "required": False,
            "label": f"{label} (Überschreibung)",
            "initial": initial,
        }
        if field_type == "euro":
            return forms.DecimalField(
                max_digits=10,
                decimal_places=2,
                widget=EuroDecimalWidget,
                **common,
            )
        if field_type == "decimal":
            return forms.DecimalField(max_digits=10, decimal_places=2, **common)
        if field_type == "integer":
            return forms.IntegerField(min_value=0, **common)
        return forms.CharField(**common)

    def save_model(self, request, obj, form, change):
        if self.is_edit(request):
            calcs = obj.calculations
            new_overrides: dict[str, str] = {}
            for key, entry in calcs.items():
                if not entry["overridable"] or not entry["override_key"]:
                    continue
                override_key = entry["override_key"]
                value = form.cleaned_data.get(f"override_{override_key}")
                if value is not None:
                    new_overrides[override_key] = str(value)
            obj.overrides = new_overrides

        super().save_model(request, obj, form, change)
        self._update_gross_salary_contract(obj)

    def _update_gross_salary_contract(self, obj) -> None:
        calcs = obj.calculations
        gross_entry = calcs.get("gross_salary")
        if gross_entry is None:
            return
        overrides = obj.overrides or {}
        if "gross_salary" in overrides:
            effective: Decimal | None = Decimal(str(overrides["gross_salary"]))
        else:
            effective = gross_entry["value"]
        obj.gross_salary_contract = effective
        obj.save(update_fields=["gross_salary_contract"])
