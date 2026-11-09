"""Consensus, average target price, upside, ranking and filtering."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from .models import Quote, Recommendation
from .scale import bucket, label

SORT_KEYS = {
    "consensus": "Konsensus",
    "upside": "Nousuvara",
    "freshness": "Tuoreus",
}


@dataclass
class ConsensusRow:
    ticker: str
    name: str
    sector: str
    consensus: float | None
    label: str
    n_recommendations: int
    avg_target: float | None
    price: float | None
    currency: str | None
    upside: float | None  # fraction, e.g. 0.12 = +12 %
    latest_date: str | None
    sources: list[str] = field(default_factory=list)
    quote_source: str | None = None
    quote_fetched_at: str | None = None


def latest_per_key(recs: Iterable[Recommendation]) -> list[Recommendation]:
    """Keep the newest snapshot per (source, ticker, analyst)."""
    best: dict[tuple[str, str, str], Recommendation] = {}
    for r in recs:
        key = (r.source_id, r.ticker, r.analyst)
        cur = best.get(key)
        if cur is None or (r.rec_date, r.fetched_at) >= (cur.rec_date, cur.fetched_at):
            best[key] = r
    return list(best.values())


def weighted_consensus(recs: Iterable[Recommendation]) -> tuple[float | None, int]:
    """Analyst-count weighted mean rating and total number of analysts."""
    total = 0
    acc = 0.0
    for r in recs:
        w = max(int(r.analyst_count), 0)
        total += w
        acc += w * r.rating
    if total == 0:
        return None, 0
    return acc / total, total


def average_target(recs: Iterable[Recommendation], currency: str | None) -> float | None:
    """Analyst-count weighted mean target price, only in the given currency.

    If currency is None, targets in any single currency are used only when all agree.
    """
    items = [r for r in recs if r.target_price is not None and r.target_price > 0]
    if currency is not None:
        items = [r for r in items if (r.currency or currency) == currency]
    elif len({r.currency for r in items}) > 1:
        return None
    total = sum(max(r.analyst_count, 1) for r in items)
    if total == 0:
        return None
    return sum(max(r.analyst_count, 1) * r.target_price for r in items) / total


def upside(target: float | None, price: float | None) -> float | None:
    if target is None or price is None or price <= 0:
        return None
    return target / price - 1


def pick_quote(quotes: Iterable[Quote], preferred_currency: str | None) -> Quote | None:
    """Newest quote, preferring the stock's own currency."""
    qs = list(quotes)
    if not qs:
        return None
    if preferred_currency:
        same = [q for q in qs if q.currency == preferred_currency]
        if same:
            qs = same
    return max(qs, key=lambda q: (q.as_of or "", q.fetched_at or ""))


def build_rows(recs: Iterable[Recommendation], quotes: Iterable[Quote], stocks: Iterable[dict]
               ) -> list[ConsensusRow]:
    """Compute one ConsensusRow per stock that has at least one recommendation."""
    latest = latest_per_key(recs)
    by_ticker: dict[str, list[Recommendation]] = {}
    for r in latest:
        by_ticker.setdefault(r.ticker, []).append(r)
    quotes_by: dict[str, list[Quote]] = {}
    for q in quotes:
        quotes_by.setdefault(q.ticker, []).append(q)
    meta = {s["ticker"]: s for s in stocks}

    rows: list[ConsensusRow] = []
    for ticker, items in by_ticker.items():
        m = meta.get(ticker, {})
        stock_ccy = m.get("currency") or None
        q = pick_quote(quotes_by.get(ticker, []), stock_ccy)
        price_ccy = q.currency if q else stock_ccy
        cons, n = weighted_consensus(items)
        tgt = average_target(items, price_ccy)
        rows.append(
            ConsensusRow(
                ticker=ticker,
                name=m.get("name", ticker),
                sector=m.get("sector", "") or "",
                consensus=cons,
                label=label(cons),
                n_recommendations=n,
                avg_target=tgt,
                price=q.price if q else None,
                currency=price_ccy,
                upside=upside(tgt, q.price if q else None),
                latest_date=max(r.rec_date for r in items),
                sources=sorted({r.source_id for r in items}),
                quote_source=q.source_id if q else None,
                quote_fetched_at=q.fetched_at if q else None,
            )
        )
    return rows


def filter_rows(rows: Iterable[ConsensusRow], labels: Iterable[str] | None = None,
                sectors: Iterable[str] | None = None) -> list[ConsensusRow]:
    out = list(rows)
    if labels:
        wanted = set(labels)
        out = [r for r in out if r.label in wanted]
    if sectors:
        wanted_s = set(sectors)
        out = [r for r in out if r.sector in wanted_s]
    return out


def sort_rows(rows: Iterable[ConsensusRow], key: str = "consensus") -> list[ConsensusRow]:
    """Sort best-first. Missing values always go last."""
    rows = list(rows)
    if key == "consensus":
        return sorted(rows, key=lambda r: (
            r.consensus is None,
            -(r.consensus or 0),
            -r.n_recommendations,
            r.upside is None,
            -(r.upside or 0),
            r.name,
        ))
    if key == "upside":
        return sorted(rows, key=lambda r: (r.upside is None, -(r.upside or 0), r.name))
    if key == "freshness":
        # ISO dates sort lexicographically; invert by sorting descending in two passes.
        with_date = sorted([r for r in rows if r.latest_date], key=lambda r: r.name)
        with_date.sort(key=lambda r: r.latest_date, reverse=True)
        return with_date + sorted([r for r in rows if not r.latest_date], key=lambda r: r.name)
    raise ValueError(f"unknown sort key: {key}")


def consensus_bucket(row: ConsensusRow) -> int | None:
    return bucket(row.consensus)
