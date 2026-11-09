"""Finnhub (https://finnhub.io) – official REST API, free tier.

Endpoints used:
- /stock/recommendation  monthly strongBuy/buy/hold/sell/strongSell counts (free tier)
- /quote                 current price
- /stock/profile2        name, industry, currency
- /stock/price-target    consensus target price (premium on Finnhub; 403 handled gracefully)

The API key is sent in the X-Finnhub-Token header so it never appears in URLs or logs.
"""
from __future__ import annotations

from datetime import UTC, datetime

import requests

from ..config import Settings
from ..models import Quote, Recommendation, SourceResult, Stock, StockInfo
from ..scale import FINNHUB_FIELDS, weighted_counts
from .base import USER_AGENT, RateLimiter, SourceAdapter

BASE_URL = "https://finnhub.io/api/v1"
DOCS = {
    "recommendation": "https://finnhub.io/docs/api/recommendation-trends",
    "price-target": "https://finnhub.io/docs/api/price-target",
    "quote": "https://finnhub.io/docs/api/quote",
}
MAX_CONSECUTIVE_DENIED = 3
HISTORY_MONTHS = 12


class AccessDenied(Exception):
    pass


class FinnhubSource(SourceAdapter):
    id = "finnhub"
    name = "Finnhub"
    homepage = "https://finnhub.io"
    description = ("Virallinen API (ilmainen taso). Analyytikkojen suositusmäärät kuukausittain; "
                   "tavoitehinta vain jos tilaus sallii.")

    def __init__(self, session: requests.Session | None = None, min_interval: float = 1.05,
                 sleep=None):
        self._session = session
        self._limiter = RateLimiter(min_interval, **({"sleep": sleep} if sleep else {}))

    # -- contract ------------------------------------------------------------------------
    def availability(self, settings: Settings) -> tuple[bool, str]:
        if not settings.finnhub_api_key:
            return False, "FINNHUB_API_KEY puuttuu (.env) – käytössä demotila"
        return True, ""

    def default_symbol(self, stock: Stock) -> str | None:
        # The free tier denies Helsinki (.HE) symbols, so Helsinki stocks need an explicit
        # watchlist mapping (usually the company's US ADR/OTC symbol). Others use the ticker.
        return None if stock.exchange == "XHEL" else stock.ticker

    @staticmethod
    def is_native(stock: Stock, symbol: str) -> bool:
        """True if the symbol trades in the stock's own listing/currency.

        For a US ADR of a Helsinki stock, Finnhub's recommendation trends describe the same
        company, but its quote and price target are in USD per ADR (ratio may differ from 1),
        so only recommendations are used.
        """
        if stock.exchange == "XHEL":
            return symbol.upper().endswith(".HE")
        return True

    def fetch(self, stocks: list[Stock], settings: Settings) -> SourceResult:
        result = SourceResult()
        session = self._session or requests.Session()
        session.headers.update({"X-Finnhub-Token": settings.finnhub_api_key or "",
                                "User-Agent": USER_AGENT})
        denied: dict[str, int] = {}
        disabled: set[str] = set()

        def call(endpoint: str, symbol: str):
            if endpoint in disabled:
                return None
            self._limiter.wait()
            resp = session.get(f"{BASE_URL}/{endpoint}", params={"symbol": symbol},
                               timeout=settings.http_timeout)
            if resp.status_code in (401, 403):
                denied[endpoint] = denied.get(endpoint, 0) + 1
                if denied[endpoint] >= MAX_CONSECUTIVE_DENIED:
                    disabled.add(endpoint)
                    result.notes.append(
                        f"/{endpoint}: pääsy evätty ({resp.status_code}) – ei käytettävissä "
                        "nykyisellä tilauksella, ohitettu tällä päivityskerralla")
                raise AccessDenied(f"/{endpoint} {symbol}: HTTP {resp.status_code}")
            if resp.status_code == 429:
                raise RuntimeError(f"/{endpoint} {symbol}: kutsuraja ylittyi (429)")
            resp.raise_for_status()
            denied[endpoint] = 0
            return resp.json()

        for stock in stocks:
            symbol = self.symbol_for(stock)
            if not symbol:
                continue
            try:
                trends = call("stock/recommendation", symbol) or []
                result.recommendations.extend(self.parse_trends(stock.ticker, symbol, trends))
            except AccessDenied as exc:
                result.errors.append(str(exc))
            except Exception as exc:  # network etc.
                result.errors.append(f"{symbol} suositukset: {exc}")

            if not self.is_native(stock, symbol):
                continue  # ADR mapping: recommendations only

            try:
                q = call("quote", symbol)
                quote = self.parse_quote(stock, symbol, q) if q else None
                if quote:
                    result.quotes.append(quote)
            except Exception as exc:
                result.errors.append(f"{symbol} kurssi: {exc}")

            try:
                pt = call("stock/price-target", symbol)
                if pt:
                    rec = self.parse_price_target(stock, symbol, pt, result.recommendations)
                    if rec:
                        result.recommendations.append(rec)
            except AccessDenied:
                pass  # premium feature; summarised once in notes
            except Exception as exc:
                result.errors.append(f"{symbol} tavoitehinta: {exc}")

            if not stock.sector:
                try:
                    prof = call("stock/profile2", symbol)
                    if prof:
                        result.stock_info.append(StockInfo(
                            ticker=stock.ticker, name=prof.get("name") or None,
                            sector=prof.get("finnhubIndustry") or None,
                            currency=prof.get("currency") or None))
                except Exception:
                    pass
        return result

    # -- parsing (pure, unit tested) ------------------------------------------------------
    def parse_trends(self, ticker: str, symbol: str, trends: list[dict]) -> list[Recommendation]:
        """One snapshot per monthly period (most recent HISTORY_MONTHS)."""
        recs = []
        for t in sorted(trends, key=lambda x: x.get("period", ""))[-HISTORY_MONTHS:]:
            mean, n = weighted_counts(t, FINNHUB_FIELDS)
            if mean is None:
                continue
            raw = "/".join(f"{k}:{int(t.get(k) or 0)}" for k in FINNHUB_FIELDS)
            recs.append(Recommendation(
                source_id=self.id, ticker=ticker, analyst="", rating_raw=raw, rating=mean,
                analyst_count=n, rec_date=str(t.get("period", ""))[:10],
                url=f"{DOCS['recommendation']}#{symbol}",
            ))
        return recs

    def parse_quote(self, stock: Stock, symbol: str, q: dict) -> Quote | None:
        price = q.get("c")
        if not price:
            return None
        ts = q.get("t")
        as_of = (datetime.fromtimestamp(ts, UTC).replace(microsecond=0).isoformat()
                 if ts else "")
        return Quote(ticker=stock.ticker, source_id=self.id, price=float(price),
                     currency=stock.currency, as_of=as_of, url=f"{DOCS['quote']}#{symbol}")

    def parse_price_target(self, stock: Stock, symbol: str, pt: dict,
                           trends: list[Recommendation]) -> Recommendation | None:
        """Attach the consensus target to the latest trend snapshot (same analysts)."""
        target = pt.get("targetMean") or pt.get("targetMedian")
        if not target:
            return None
        latest = [r for r in trends if r.ticker == stock.ticker]
        if not latest:
            return None
        base = max(latest, key=lambda r: r.rec_date)
        trends.remove(base)
        base.target_price = float(target)
        base.currency = stock.currency
        upd = str(pt.get("lastUpdated") or "")[:10]
        if upd > base.rec_date:
            base.rec_date = upd
        return base
