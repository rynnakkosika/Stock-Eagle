"""Detect recommendation upgrades/downgrades and target-price changes from snapshot history."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from .models import Recommendation
from .scale import bucket, label

UPGRADE = "Nosto"
DOWNGRADE = "Lasku"
TARGET_ONLY = "Tavoitehinta"
INITIATED = "Uusi"


@dataclass
class Change:
    ticker: str
    source_id: str
    analyst: str
    date: str
    kind: str  # Nosto | Lasku | Tavoitehinta | Uusi
    direction: int  # +1, -1, 0
    old_rating: float | None
    new_rating: float
    old_label: str
    new_label: str
    old_target: float | None
    new_target: float | None
    url: str
    fetched_at: str

    @property
    def target_change_pct(self) -> float | None:
        if self.old_target and self.new_target:
            return self.new_target / self.old_target - 1
        return None


def _targets_differ(a: float | None, b: float | None, tol: float = 1e-6) -> bool:
    if a is None and b is None:
        return False
    if a is None or b is None:
        return True
    return abs(a - b) > tol


def detect_changes(recs: Iterable[Recommendation], include_initial: bool = False) -> list[Change]:
    """Compare consecutive snapshots per (source, ticker, analyst).

    A change in the normalized rating bucket is an upgrade/downgrade; otherwise a target price
    change is reported as a target-only change. Identical consecutive snapshots produce nothing.
    """
    groups: dict[tuple[str, str, str], list[Recommendation]] = {}
    for r in recs:
        groups.setdefault((r.source_id, r.ticker, r.analyst), []).append(r)

    changes: list[Change] = []
    for (source_id, ticker, analyst), items in groups.items():
        items.sort(key=lambda r: (r.rec_date, r.fetched_at))
        prev: Recommendation | None = None
        for cur in items:
            if prev is None:
                if include_initial:
                    changes.append(_mk(cur, None, INITIATED, 0))
                prev = cur
                continue
            b_old, b_new = bucket(prev.rating), bucket(cur.rating)
            if b_new != b_old:
                direction = 1 if (b_new or 0) > (b_old or 0) else -1
                changes.append(_mk(cur, prev, UPGRADE if direction > 0 else DOWNGRADE, direction))
            elif _targets_differ(prev.target_price, cur.target_price):
                changes.append(_mk(cur, prev, TARGET_ONLY, 0))
            prev = cur
    changes.sort(key=lambda c: (c.date, c.fetched_at), reverse=True)
    return changes


def _mk(cur: Recommendation, prev: Recommendation | None, kind: str, direction: int) -> Change:
    return Change(
        ticker=cur.ticker,
        source_id=cur.source_id,
        analyst=cur.analyst,
        date=cur.rec_date,
        kind=kind,
        direction=direction,
        old_rating=prev.rating if prev else None,
        new_rating=cur.rating,
        old_label=label(prev.rating) if prev else "–",
        new_label=label(cur.rating),
        old_target=prev.target_price if prev else None,
        new_target=cur.target_price,
        url=cur.url,
        fetched_at=cur.last_seen_at or cur.fetched_at,
    )


def recent(changes: Iterable[Change], days: int, today: date | None = None) -> list[Change]:
    cutoff = ((today or date.today()) - timedelta(days=days)).isoformat()
    return [c for c in changes if c.date >= cutoff]
