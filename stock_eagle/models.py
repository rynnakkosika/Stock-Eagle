"""Shared data structures."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Stock:
    """A stock from the watchlist."""

    ticker: str
    name: str
    sector: str = ""
    exchange: str = "XHEL"
    currency: str = "EUR"
    ids: dict[str, str] = field(default_factory=dict, hash=False, compare=False)

    def source_id(self, source: str, default: str | None = None) -> str | None:
        return self.ids.get(source, default)


@dataclass
class Recommendation:
    """One source's recommendation for one stock at one point in time."""

    source_id: str
    ticker: str
    rating_raw: str
    rating: float  # normalized 1..5
    rec_date: str  # ISO date (YYYY-MM-DD)
    url: str
    analyst: str = ""
    analyst_count: int = 1
    target_price: float | None = None
    currency: str | None = None
    fetched_at: str = ""
    last_seen_at: str = ""


@dataclass
class Quote:
    ticker: str
    source_id: str
    price: float
    currency: str
    as_of: str
    url: str = ""
    fetched_at: str = ""


@dataclass
class StockInfo:
    """Optional metadata a source may know about a stock (name, sector)."""

    ticker: str
    name: str | None = None
    sector: str | None = None
    currency: str | None = None


@dataclass
class SourceResult:
    recommendations: list[Recommendation] = field(default_factory=list)
    quotes: list[Quote] = field(default_factory=list)
    stock_info: list[StockInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
