from __future__ import annotations

from decimal import Decimal
from typing import Literal, TypedDict

FieldType = Literal["euro", "decimal", "integer", "text"]


class CalculationEntry(TypedDict):
    value: Decimal | int | str | None
    label: str
    field_type: FieldType
    overridable: bool
    override_key: str | None
