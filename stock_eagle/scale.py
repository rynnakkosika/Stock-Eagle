"""Normalization of recommendation scales to a common 1..5 scale.

1 = Myy (sell), 2 = Vähennä (reduce), 3 = Pidä (hold), 4 = Lisää (accumulate), 5 = Osta (buy).
"""
from __future__ import annotations

import math
from collections.abc import Mapping

LABELS: dict[int, str] = {1: "Myy", 2: "Vähennä", 3: "Pidä", 4: "Lisää", 5: "Osta"}
LABEL_ORDER: list[str] = [LABELS[i] for i in (5, 4, 3, 2, 1)]

# Free-text synonyms (lowercase) → normalized value. Covers Finnish, English and Swedish terms.
_TEXT_MAP: dict[str, int] = {
    # 5
    "osta": 5, "buy": 5, "strong buy": 5, "strongbuy": 5, "köp": 5, "outperform": 5,
    # 4
    "lisää": 4, "lisaa": 4, "accumulate": 4, "add": 4, "overweight": 4, "öka": 4,
    "moderate buy": 4,
    # 3
    "pidä": 3, "pida": 3, "hold": 3, "neutral": 3, "market perform": 3, "behåll": 3,
    "equal weight": 3, "equal-weight": 3,
    # 2
    "vähennä": 2, "vahenna": 2, "reduce": 2, "underweight": 2, "minska": 2,
    "moderate sell": 2,
    # 1
    "myy": 1, "sell": 1, "strong sell": 1, "strongsell": 1, "sälj": 1, "underperform": 1,
}

# Finnhub recommendation-trend count fields → normalized value.
FINNHUB_FIELDS: dict[str, int] = {
    "strongBuy": 5,
    "buy": 4,
    "hold": 3,
    "sell": 2,
    "strongSell": 1,
}


def normalize_text(value: str) -> int | None:
    """Map a textual recommendation to 1..5, or None if unknown."""
    if value is None:
        return None
    key = " ".join(str(value).strip().lower().replace("_", " ").split())
    return _TEXT_MAP.get(key)


def normalize_numeric(value: float, low: float, high: float, higher_is_better: bool = True) -> float:
    """Linearly map a value from [low, high] to [1, 5]."""
    if high == low:
        raise ValueError("high and low must differ")
    if not (min(low, high) <= value <= max(low, high)):
        raise ValueError(f"value {value} outside scale [{low}, {high}]")
    frac = (value - low) / (high - low)
    if not higher_is_better:
        frac = 1 - frac
    return 1 + 4 * frac


def normalize_three_level(value: str) -> int | None:
    """Three-level scale buy/hold/sell → 5/3/1."""
    key = str(value).strip().lower()
    return {"buy": 5, "osta": 5, "hold": 3, "pidä": 3, "neutral": 3, "sell": 1, "myy": 1}.get(key)


def weighted_counts(counts: Mapping[str, int | None], mapping: Mapping[str, int] = FINNHUB_FIELDS
                    ) -> tuple[float | None, int]:
    """Weighted mean of a distribution of recommendation counts.

    Returns (mean rating 1..5 or None if no analysts, total analyst count).
    """
    total = 0
    acc = 0.0
    for field_name, value in mapping.items():
        n = int(counts.get(field_name) or 0)
        if n < 0:
            raise ValueError("counts must be non-negative")
        total += n
        acc += n * value
    if total == 0:
        return None, 0
    return acc / total, total


def bucket(rating: float | None) -> int | None:
    """Round a 1..5 rating to the nearest integer step (halves round up)."""
    if rating is None or (isinstance(rating, float) and math.isnan(rating)):
        return None
    r = max(1.0, min(5.0, float(rating)))
    return int(math.floor(r + 0.5))


def label(rating: float | None) -> str:
    b = bucket(rating)
    return LABELS[b] if b is not None else "–"
