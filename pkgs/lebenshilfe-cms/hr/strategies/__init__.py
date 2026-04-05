from __future__ import annotations

from hr.strategies.base import CalculationStrategy
from hr.strategies.v2026 import V2026Strategy

_REGISTRY: dict[str, type[CalculationStrategy]] = {
    "2026": V2026Strategy,
}

_DEFAULT_VERSION = "2026"


def get_strategy(version: str | None = None) -> CalculationStrategy:
    key = version or _DEFAULT_VERSION
    cls = _REGISTRY.get(key)
    if cls is None:
        raise ValueError(f"Unbekannte Berechnungsversion: {key!r}")
    return cls()


__all__ = ["get_strategy", "CalculationStrategy", "V2026Strategy"]
