"""Financial Modeling Prep (https://financialmodelingprep.com) – official REST API.

Endpoints (stable API):
- /stable/grades-consensus?symbol=      strongBuy/buy/hold/sell/strongSell counts + consensus
- /stable/price-target-consensus?symbol= targetConsensus/targetMedian/targetHigh/targetLow

Enabled only when FMP_API_KEY is set. FMP takes the key as an `apikey` query parameter, so the
key is scrubbed from every message this adapter produces (it never reaches the UI or logs).

Symbol resolution per stock (first that returns data wins):
1. watchlist `ids.fmp`,
2. the Helsinki listing `<TICKER>.HE` (may be denied on the free plan),
3. the US ADR/OTC symbol from `ids.finnhub` (recommendations only: an ADR's target is in USD
   per ADR, which does not match the Helsinki share).
If the first three `.HE` attempts are all denied, `.HE` is skipped for the rest of the run to
save the daily quota.
"""
from __future__ import annotations

import os
from datetime import date

import requests

from ..config import Settings
from ..models import Recommendation, SourceResult, Stock
from ..scale import FINNHUB_FIELDS, weighted_counts
from .base import USER_AGENT, RateLimiter, SourceAdapter

BASE_URL = "https://financialmodelingprep.com/stable"
DOCS = {
    "grades": "https://site.financialmodelingprep.com/developer/docs/stable/grades-summary",
    "target": "https://site.financialmodelingprep.com/developer/docs/stable/price-target-consensus",
}
MAX_DENIED_HE = 3


class Denied(Exception):
    pass


def _api_key() -> str | None:
    return (os.environ.get("FMP_API_KEY") or "").strip() or None


class FmpSource(SourceAdapter):
    id = "fmp"
    name = "Financial Modeling Prep"
    homepage = "https://financialmodelingprep.com"
    description = ("Virallinen API (ilmainen taso, n. 250 kutsua/vrk). Analyytikkojen "
                   "suositusmäärät ja tavoitehintakonsensus. Käytössä, kun FMP_API_KEY on asetettu.")

    def __init__(self, session: requests.Session | None = None, min_interval: float = 0.3,
                 sleep=None, api_key: str | None = None, today: date | None = None):
        self._session = session
        self._limiter = RateLimiter(min_interval, **({"sleep": sleep} if sleep else {}))
        self._key = api_key
        self._today = today

    def key(self) -> str | None:
        return self._key or _api_key()

    def availability(self, settings: Settings) -> tuple[bool, str]:
        if not self.key():
            return False, "FMP_API_KEY puuttuu (.env / Secrets)"
        return True, ""

    def candidates(self, stock: Stock) -> list[tuple[str, bool]]:
        """[(symbol, native)] in the order they are tried."""
        if stock.ids.get(self.id):
            sym = stock.ids[self.id]
            return [(sym, stock.exchange != "XHEL" or sym.upper().endswith(".HE"))]
        if stock.exchange != "XHEL":
            return [(stock.ticker, True)]
        out = [(f"{stock.ticker}.HE", True)]
        if stock.ids.get("finnhub"):
            out.append((stock.ids["finnhub"], False))
        return out

    def _scrub(self, text: str) -> str:
        key = self.key()
        return text.replace(key, "***") if key else text

    def fetch(self, stocks: list[Stock], settings: Settings) -> SourceResult:
        result = SourceResult()
        session = self._session or requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})
        key = self.key() or ""
        today = (self._today or date.today()).isoformat()
        he_denied = 0
        he_disabled = False

        def call(endpoint: str, symbol: str):
            self._limiter.wait()
            try:
                resp = session.get(f"{BASE_URL}/{endpoint}",
                                   params={"symbol": symbol, "apikey": key},
                                   timeout=settings.http_timeout)
            except Exception as exc:  # message may contain the URL with the key
                raise RuntimeError(self._scrub(f"{type(exc).__name__}: {exc}")) from None
            if resp.status_code in (401, 402, 403):
                raise Denied(f"HTTP {resp.status_code}")
            if resp.status_code == 429:
                raise RuntimeError("päivittäinen kutsuraja täynnä (429)")
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}")
            data = resp.json()
            if isinstance(data, dict) and ("Error Message" in data or "error" in data):
                msg = str(data.get("Error Message") or data.get("error"))
                if "premium" in msg.lower() or "subscription" in msg.lower() or "limit" in msg.lower():
                    raise Denied(self._scrub(msg)[:120])
                raise RuntimeError(self._scrub(msg)[:200])
            return data

        for stock in stocks:
            got = False
            for symbol, native in self.candidates(stock):
                if native and symbol.upper().endswith(".HE") and he_disabled:
                    continue
                try:
                    grades = call("grades-consensus", symbol)
                except Denied:
                    if native and symbol.upper().endswith(".HE"):
                        he_denied += 1
                        if he_denied >= MAX_DENIED_HE and not he_disabled:
                            he_disabled = True
                            result.notes.append(
                                "Helsingin .HE-tunnukset eivät ole käytettävissä nykyisellä "
                                "FMP-tilauksella – käytetään USA-tunnuksia (ADR)")
                    continue
                except Exception as exc:
                    result.errors.append(f"{stock.ticker} ({symbol}): {exc}")
                    break
                rec = self.parse_grades(stock, symbol, grades, today)
                if rec is None:
                    continue  # no coverage under this symbol, try the next one
                if native:
                    try:
                        target = call("price-target-consensus", symbol)
                        self.attach_target(rec, target, stock)
                    except Denied:
                        pass
                    except Exception as exc:
                        result.errors.append(f"{stock.ticker} tavoitehinta: {exc}")
                result.recommendations.append(rec)
                got = True
                break
            if not got and stock.ids.get(self.id):
                result.errors.append(f"{stock.ticker}: ei dataa tunnuksella {stock.ids[self.id]}")
        return result

    # -- parsing (pure, unit tested) ------------------------------------------------------
    def parse_grades(self, stock: Stock, symbol: str, data, today: str) -> Recommendation | None:
        row = data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else None
        if not row:
            return None
        mean, n = weighted_counts(row, FINNHUB_FIELDS)
        if mean is None:
            return None
        raw = "/".join(f"{k}:{int(row.get(k) or 0)}" for k in FINNHUB_FIELDS)
        if row.get("consensus"):
            raw = f"{row['consensus']} ({raw})"
        return Recommendation(
            source_id=self.id, ticker=stock.ticker, analyst="", rating_raw=raw, rating=mean,
            analyst_count=n, rec_date=today, url=f"{DOCS['grades']}#{symbol}",
        )

    @staticmethod
    def attach_target(rec: Recommendation, data, stock: Stock) -> None:
        row = data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else None
        if not row:
            return
        target = row.get("targetConsensus") or row.get("targetMedian")
        if target:
            rec.target_price = float(target)
            rec.currency = stock.currency
