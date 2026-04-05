from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from base.calculated_fields.types import CalculationEntry

if TYPE_CHECKING:
    from hr.models import Employment


class CalculationStrategy(ABC):
    """Abstract base for versioned Employment calculation strategies."""

    @abstractmethod
    def calculate(self, employment: Employment) -> dict[str, CalculationEntry]:
        """
        Compute all derived fields for an Employment instance.
        Returns an ordered dict keyed by stable English identifiers.
        Dict order defines display order in the admin.
        """
        ...

    @classmethod
    @abstractmethod
    def field_schema(cls) -> dict[str, CalculationEntry]:
        """
        Return the field schema template with value=None.
        Used by CalculatedFieldsMixin at admin startup to register display
        methods without requiring a real model instance.
        """
        ...
