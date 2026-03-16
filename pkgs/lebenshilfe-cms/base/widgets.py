from django.forms import MultiWidget, NumberInput
from unfold.widgets import UnfoldPrefixSuffixMixin, INPUT_CLASSES

class HourMinuteDurationWidget(MultiWidget):
    template_name = "unfold/widgets/range.html" 

    def __init__(self, attrs=None):
        widgets = (
            NumberInput(attrs={
                "placeholder": "Stunden", 
                "class": " ".join(INPUT_CLASSES),
                "min": "0"
            }),
            NumberInput(attrs={
                "placeholder": "Minuten", 
                "class": " ".join(INPUT_CLASSES),
                "min": "0",
                "max": "59"
            }),
        )
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            total_seconds = int(value.total_seconds())
            return [total_seconds // 3600, (total_seconds % 3600) // 60]
        return [None, None]

    def value_from_datadict(self, data, files, name):
        parts = super().value_from_datadict(data, files, name)
        if parts[0] or parts[1]:
            hours = int(parts[0] or 0)
            minutes = int(parts[1] or 0)
            return f"{hours}:{minutes:02d}:00"
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

