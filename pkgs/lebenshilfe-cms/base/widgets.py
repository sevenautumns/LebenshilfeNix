from django.forms import MultiWidget, NumberInput, Select
from unfold.widgets import UnfoldPrefixSuffixMixin, INPUT_CLASSES
from django.utils.dateparse import parse_duration
from datetime import timedelta, date


class HourMinuteDurationWidget(MultiWidget):
    template_name = "unfold/widgets/range.html"

    def __init__(self, attrs=None):
        widgets = (
            NumberInput(
                attrs={
                    "placeholder": "Stunden",
                    "class": " ".join(INPUT_CLASSES),
                    "min": "0",
                }
            ),
            NumberInput(
                attrs={
                    "placeholder": "Minuten",
                    "class": " ".join(INPUT_CLASSES),
                    "min": "0",
                    "max": "59",
                }
            ),
        )
        super().__init__(widgets, attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        for subwidget in context["widget"]["subwidgets"]:
            subwidget["attrs"]["x-model.fill"] = subwidget["name"]
        return context

    def decompress(self, value):
        if value:
            if isinstance(value, str):
                value = parse_duration(value)

            if isinstance(value, timedelta):
                total_seconds = int(value.total_seconds())
                return [total_seconds // 3600, (total_seconds % 3600) // 60]
        return [None, None]

    def value_from_datadict(self, data, files, name):
        parts = super().value_from_datadict(data, files, name)
        if parts[0] or parts[1]:
            hours = int(parts[0] or 0)
            minutes = int(parts[1] or 0)
            return timedelta(hours=hours, minutes=minutes)
        return None


class MonthWidget(MultiWidget):
    template_name = "unfold/widgets/range.html"

    def __init__(self, attrs=None):
        widgets = (
            Select(
                attrs={"class": " ".join(INPUT_CLASSES)},
                choices=[
                    (1, "Januar"),
                    (2, "Februar"),
                    (3, "März"),
                    (4, "April"),
                    (5, "Mai"),
                    (6, "Juni"),
                    (7, "Juli"),
                    (8, "August"),
                    (9, "September"),
                    (10, "Oktober"),
                    (11, "November"),
                    (12, "Dezember"),
                ],
            ),
            NumberInput(
                attrs={
                    "placeholder": "Jahr",
                    "class": " ".join(INPUT_CLASSES),
                    "min": "1900",
                    "max": "2100",
                }
            ),
        )
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if isinstance(value, date):
            return [value.month, value.year]
        if isinstance(value, str) and value:
            parts = value.split("-")
            if len(parts) >= 2:
                return [int(parts[1]), int(parts[0])]
        return [None, None]

    def value_from_datadict(self, data, files, name):
        parts = super().value_from_datadict(data, files, name)
        month, year = parts[0], parts[1]
        if month and year:
            try:
                return date(int(year), int(month), 1)
            except (ValueError, TypeError):
                return None
        return None


class EuroDecimalWidget(UnfoldPrefixSuffixMixin, NumberInput):
    template_name = "unfold/widgets/text.html"

    def __init__(self, attrs=None):
        default_attrs = {
            "class": " ".join(INPUT_CLASSES),
            "prefix_icon": "euro_symbol",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
