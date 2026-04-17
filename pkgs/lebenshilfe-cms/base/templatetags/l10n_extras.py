from decimal import Decimal

from django import template
from django.utils.formats import number_format

register = template.Library()


@register.filter
def localfloat(value: Decimal | float | str, decimal_pos: int = 2) -> str:
    return number_format(value, decimal_pos=int(decimal_pos), use_l10n=True)
