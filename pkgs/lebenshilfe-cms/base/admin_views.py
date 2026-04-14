from datetime import date
from urllib.parse import urlencode

from django.contrib import messages
from django import forms
from django.core.paginator import EmptyPage, InvalidPage, Paginator
from django.db.models import F, QuerySet, Value, CharField
from django.http import Http404, HttpRequest
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.formats import number_format
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView, View
from unfold.views import UnfoldModelAdminViewMixin


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------


def render_label(text: str, variant: str = "default", size: str = "md") -> str:
    """Renders an Unfold badge using Unfold's own label template.

    Args:
        text: The label text to display.
        variant: One of 'info', 'success', 'warning', 'danger', 'primary', or 'default'.
        size: 'md' (h-5) or larger (h-6). Defaults to 'md'.
    """
    return mark_safe(
        render_to_string(
            "unfold/helpers/label.html",
            {"type": variant, "text": text, "size": size},
        )
    )


class AdminViewMixin:
    """Gemeinsamer Mixin für alle Custom Admin Views.

    Stellt get_media() bereit, das korrekt jsi18n + Widget-Media lädt.
    Muss vor UnfoldModelAdminViewMixin in der MRO stehen.
    """

    def get_media(self, form=None) -> forms.Media:
        return (
            self.model_admin.media
            + (form.media if form else forms.Media())
            + forms.Media(js=[reverse("javascript-catalog")])
        )


# ---------------------------------------------------------------------------
# Calculator views
# ---------------------------------------------------------------------------


class BaseCalculatorView(AdminViewMixin, UnfoldModelAdminViewMixin, TemplateView):
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
                "media": self.get_media(form),
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


class UnionListMixin(AdminViewMixin):
    """Mixin für Union-Listen-Views aus zwei QuerySets mit Form-Filtern und Paginierung.

    Sortierung: URL-Parameter ?sort=-field1,field2 (kommasepariert, "-" = absteigend).
    Klick auf inaktive Spalte fügt sie vorne ein (ASC). Klick auf aktive Spalte bringt
    sie nach vorne und togglet die Richtung. Der Pfeil-Icon togglet die Richtung in-place.
    """

    default_sort_field: str = "start_date"
    default_sort_dir: str = "desc"
    per_page: int = 50

    # Interne Konstante: GET-Parameter die nicht zur Filterform gehören
    _SORT_PARAMS: frozenset[str] = frozenset({"sort", "p"})

    def get_queryset_a(self, request: HttpRequest) -> QuerySet:
        raise NotImplementedError

    def get_queryset_b(self, request: HttpRequest) -> QuerySet:
        raise NotImplementedError

    def get_columns(self) -> list[tuple[str, str | None]]:
        """Gibt Spaltendefinitionen zurück: Liste von (Label, sort_field_or_None).

        sort_field kann sein:
        - Direktes Feld: "start_date", "end_date"
        - Annotation: "_row_type" (bereits im UNION-SELECT vorhanden)
        - Relationales Feld: "student__last_name" (wird automatisch annotiert)
        - None: Spalte ist nicht sortierbar
        """
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

    def _resolve_sort(self, request: HttpRequest) -> list[tuple[str, bool]]:
        """Parst ?sort=-field1,field2 und gibt eine geordnete Liste von (field, ascending) zurück.

        Validiert jeden Eintrag gegen die erlaubten sort_fields aus get_columns().
        Fällt auf den konfigurierten Default zurück wenn keine gültigen Felder angegeben.
        """
        allowed = {sf for _, sf in self.get_columns() if sf}
        raw = request.GET.get("sort", "")
        specs: list[tuple[str, bool]] = []
        seen: set[str] = set()
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            ascending = not part.startswith("-")
            field = part.lstrip("-")
            if field in allowed and field not in seen:
                specs.append((field, ascending))
                seen.add(field)
        if not specs:
            specs = [(self.default_sort_field, self.default_sort_dir == "asc")]
        return specs

    @staticmethod
    def _actual_field(sort_field: str) -> str:
        """Gibt den tatsächlichen Feldnamen nach Annotation-Transformation zurück.

        Relationale Felder (student__last_name) werden als student_last_name_sort annotiert.
        """
        if "__" in sort_field:
            return sort_field.replace("__", "_") + "_sort"
        return sort_field

    def _get_id_union_queryset(self, request: HttpRequest, form) -> QuerySet:
        """Baut ein kombiniertes QuerySet aus (pk, _row_type, ...sort_fields) für die Paginierung."""
        sort_specs = self._resolve_sort(request)

        qs_a = self._apply_filter_form(self.get_queryset_a(request), form).annotate(
            _row_type=Value("A", output_field=CharField())
        )
        qs_b = self._apply_filter_form(self.get_queryset_b(request), form).annotate(
            _row_type=Value("B", output_field=CharField())
        )

        # Alle Sort-Felder annotieren und in den SELECT aufnehmen.
        # Relationale Felder (mit "__") werden als Annotation materialisiert,
        # da UNION-Subqueries keine Spaltenaliase über JOINs hinweg erlauben.
        select_fields = ["pk", "_row_type"]
        ordering_exprs = []
        for sort_field, ascending in sort_specs:
            actual = self._actual_field(sort_field)
            if "__" in sort_field:
                qs_a = qs_a.annotate(**{actual: F(sort_field)})
                qs_b = qs_b.annotate(**{actual: F(sort_field)})
            if actual not in select_fields:
                select_fields.append(actual)
            expr = (
                F(actual).asc(nulls_last=True)
                if ascending
                else F(actual).desc(nulls_last=True)
            )
            ordering_exprs.append(expr)

        # Sortierung der Teilabfragen löschen — ORDER BY in UNION-Subqueries ist
        # im SQL-Standard nicht erlaubt. Die Gesamtsortierung kommt danach.
        combined = (
            qs_a.values(*select_fields)
            .order_by()
            .union(qs_b.values(*select_fields).order_by())
        )
        return combined.order_by(*ordering_exprs)

    def _fetch_full_page_objects(self, request, id_type_list) -> list:
        """Lädt die vollständigen Modellinstanzen für eine Liste von (id, type) Paaren."""
        ids_a = [item["pk"] for item in id_type_list if item["_row_type"] == "A"]
        ids_b = [item["pk"] for item in id_type_list if item["_row_type"] == "B"]

        objs_a = (
            {obj.pk: obj for obj in self.get_queryset_a(request).filter(pk__in=ids_a)}
            if ids_a
            else {}
        )
        objs_b = (
            {obj.pk: obj for obj in self.get_queryset_b(request).filter(pk__in=ids_b)}
            if ids_b
            else {}
        )

        # In der ursprünglichen Reihenfolge der Paginierung zusammensetzen
        final_list = []
        for item in id_type_list:
            pk, row_type = item["pk"], item["_row_type"]
            if row_type == "A" and pk in objs_a:
                final_list.append(objs_a[pk])
            elif row_type == "B" and pk in objs_b:
                final_list.append(objs_b[pk])

        return final_list

    def _sort_specs_to_param(self, specs: list[tuple[str, bool]]) -> str:
        """Serialisiert Sort-Specs als URL-Parameter-Wert: "-field1,field2"."""
        return ",".join(f"{'' if asc else '-'}{f}" for f, asc in specs)

    def _build_column_headers(self, request: HttpRequest) -> list[dict]:
        """Baut Column-Header-Metadaten für sortierbare Tabellenköpfe.

        Jeder Header enthält:
        - url_primary: Klick auf Label — inaktive Spalte vorne einfügen (ASC),
                       aktive Spalte vorne einfügen mit getoggelter Richtung
        - url_toggle: Klick auf Pfeil — Richtung in-place togglen (nur wenn aktiv)
        - remove_url: Klick auf × — Spalte aus Sort entfernen (nur wenn aktiv)
        - sort_priority: Position in der Sortierliste (1-basiert, 0 = inaktiv)
        - ascending: True/False wenn aktiv, None wenn inaktiv
        """
        sort_specs = self._resolve_sort(request)
        sort_map = {field: (i + 1, asc) for i, (field, asc) in enumerate(sort_specs)}

        result = []
        for label, sort_field in self.get_columns():
            if sort_field is None:
                result.append({"label": label, "sortable": False})
                continue

            priority, is_asc = sort_map.get(sort_field, (0, None))
            is_active = priority > 0

            # url_primary: an erste Stelle setzen — inaktiv mit ASC, aktiv mit getoggelter Richtung
            if not is_active:
                primary_specs = [(sort_field, True)] + sort_specs
            else:
                other = [(f, asc) for f, asc in sort_specs if f != sort_field]
                primary_specs = [(sort_field, not is_asc)] + other
            params_primary = request.GET.copy()
            params_primary["sort"] = self._sort_specs_to_param(primary_specs)
            params_primary.pop("p", None)

            # url_toggle: Richtung in-place togglen, Position beibehalten (nur wenn aktiv)
            if is_active:
                toggle_specs = [
                    (f, not asc if f == sort_field else asc) for f, asc in sort_specs
                ]
                params_toggle = request.GET.copy()
                params_toggle["sort"] = self._sort_specs_to_param(toggle_specs)
                params_toggle.pop("p", None)
                url_toggle = f"?{params_toggle.urlencode()}"
            else:
                url_toggle = None

            # url_remove: Spalte aus Sort entfernen (immer zeigen wenn aktiv)
            remaining = [(f, asc) for f, asc in sort_specs if f != sort_field]
            params_remove = request.GET.copy()
            if remaining:
                params_remove["sort"] = self._sort_specs_to_param(remaining)
            else:
                params_remove.pop("sort", None)
            params_remove.pop("p", None)

            result.append(
                {
                    "label": label,
                    "sortable": True,
                    "sort_field": sort_field,
                    "url_primary": f"?{params_primary.urlencode()}",
                    "url_toggle": url_toggle,
                    "remove_url": f"?{params_remove.urlencode()}"
                    if is_active
                    else None,
                    "active": is_active,
                    "ascending": is_asc if is_active else None,
                    "sort_priority": priority,
                    "multi_sort_active": len(sort_specs) > 1,
                }
            )
        return result

    def _build_table(self, page_objects) -> dict:
        return {
            "rows": [{"cols": self.get_row(obj)} for obj in page_objects],
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
        if filter_form_class:
            # Sort- und Paginierungs-Parameter von den Filter-Params trennen,
            # damit die Form bei ausschließlich aktiven Sort-Params als "ungebunden"
            # gilt und ihre Defaults (z.B. Schuljahres-Filter) korrekt anwendet.
            filter_data = {
                k: v for k, v in request.GET.items() if k not in self._SORT_PARAMS
            }
            filter_form = filter_form_class(filter_data or None)
        else:
            filter_form = None

        # 1. Paginierung auf ID-Ebene (DB-seitig)
        id_union_qs = self._get_id_union_queryset(request, filter_form)
        paginator = Paginator(id_union_qs, self.per_page)

        try:
            page_num = int(request.GET.get("p", 1))
        except (ValueError, TypeError):
            page_num = 1

        try:
            page_obj = paginator.page(page_num)
        except (EmptyPage, InvalidPage):
            page_obj = paginator.page(paginator.num_pages)

        # 2. Nur die 50 Objekte der aktuellen Seite voll auflösen (DB-seitig)
        full_objects = self._fetch_full_page_objects(request, page_obj.object_list)

        # 3. Query-String-Helfer für Pagination-Links
        params = request.GET.copy()
        params.pop("p", None)
        query_string_base = params.urlencode()

        column_headers = self._build_column_headers(request)

        ctx.update(
            {
                "title": self.title,
                "page_obj": page_obj,
                "paginator": paginator,
                "query_string_base": query_string_base,
                "filter_form": filter_form,
                "has_active_filters": self._has_active_filters(filter_form),
                "table": self._build_table(full_objects),
                "column_headers": column_headers,
                "column_labels": [col["label"] for col in column_headers],
                "breadcrumb_items": self.get_breadcrumb_items(),
                "opts": self.model_admin.model._meta,
                "media": self.get_media(filter_form),
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
