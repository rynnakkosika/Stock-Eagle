"""Inderes (https://www.inderes.fi) – public company pages.

No official public API or feed exists. robots.txt (checked 2026-11-09) allows all crawling and the
terms of use permit viewing/downloading content for the user's own personal, non-commercial use.
This adapter therefore:
- reads only the public company page of stocks in the user's watchlist,
- waits 1.5 s between requests and identifies itself with a descriptive User-Agent,
- runs only when the user presses refresh, and keeps the data local.
See DECISIONS.md. Disable with INDERES_ENABLED=false.

Data is read from the JSON that Next.js embeds into the public HTML page (__NEXT_DATA__).
"""
from __future__ import annotations

import json
import re

import requests

from ..config import Settings
from ..models import Quote, Recommendation, SourceResult, Stock, StockInfo
from .base import USER_AGENT, RateLimiter, SourceAdapter

BASE = "https://www.inderes.fi"
RATING_NAMES = {1: "Myy", 2: "Vähennä", 3: "Pidä", 4: "Lisää", 5: "Osta"}
_NEXT_DATA = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S | re.I)


class ParseError(Exception):
    pass


class InderesSource(SourceAdapter):
    id = "inderes"
    name = "Inderes"
    homepage = BASE
    description = ("Julkiset yrityssivut (oma, henkilökohtainen käyttö käyttöehtojen mukaisesti). "
                   "Yksi analyytikko per yhtiö.")

    def __init__(self, session: requests.Session | None = None, min_interval: float = 1.5,
                 sleep=None):
        self._session = session
        self._limiter = RateLimiter(min_interval, **({"sleep": sleep} if sleep else {}))

    def availability(self, settings: Settings) -> tuple[bool, str]:
        if not settings.inderes_enabled:
            return False, "INDERES_ENABLED=false"
        return True, ""

    def page_url(self, slug: str) -> str:
        return f"{BASE}/companies/{slug}"

    def fetch(self, stocks: list[Stock], settings: Settings) -> SourceResult:
        result = SourceResult()
        session = self._session or requests.Session()
        session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "fi"})
        for stock in stocks:
            slug = self.symbol_for(stock)
            if not slug:
                continue
            url = self.page_url(slug)
            try:
                self._limiter.wait()
                resp = session.get(url, timeout=settings.http_timeout)
                if resp.status_code == 404:
                    result.errors.append(f"{stock.ticker}: sivua ei löydy ({url})")
                    continue
                resp.raise_for_status()
                rec, quote, info = self.parse_page(stock, url, resp.text)
                if rec:
                    result.recommendations.append(rec)
                if quote:
                    result.quotes.append(quote)
                if info:
                    result.stock_info.append(info)
            except Exception as exc:
                result.errors.append(f"{stock.ticker}: {type(exc).__name__}: {exc}")
        return result

    # -- parsing (pure, unit tested) ------------------------------------------------------
    @staticmethod
    def extract_next_data(html: str) -> dict:
        m = _NEXT_DATA.search(html)
        if not m:
            raise ParseError("__NEXT_DATA__ puuttuu sivulta")
        return json.loads(m.group(1))

    def parse_page(self, stock: Stock, url: str, html: str
                   ) -> tuple[Recommendation | None, Quote | None, StockInfo | None]:
        data = self.extract_next_data(html)
        try:
            company = data["props"]["pageProps"]["payload"]["data"]["company"]
        except (KeyError, TypeError) as exc:
            raise ParseError("yritystietoja ei löytynyt sivun datasta") from exc
        inst = company.get("defaultInstrument") or {}
        est = ((inst.get("estimateData") or {}).get("estimates")) or {}
        if isinstance(est, list):  # tolerate either shape
            est = max(est, key=lambda e: e.get("date") or "", default={})
        currency = (inst.get("estimateData") or {}).get("researchCurrency")
        price_data = inst.get("priceData") or {}

        rec = None
        code = est.get("recommendation")
        if isinstance(code, (int, float)) and int(code) in RATING_NAMES:
            code = int(code)
            analysts = company.get("analysts") or []
            analyst = ", ".join(a.get("name", "") for a in analysts if a.get("name")) or "Inderes"
            target = est.get("targetPrice")
            rec = Recommendation(
                source_id=self.id, ticker=stock.ticker, analyst=analyst,
                rating_raw=RATING_NAMES[code], rating=float(code), analyst_count=1,
                target_price=float(target) if target else None,
                currency=currency or price_data.get("tradeCurrency") or stock.currency,
                rec_date=str(est.get("date") or "")[:10], url=url,
            )
            if not rec.rec_date:
                rec = None

        quote = None
        if price_data.get("lastPrice"):
            quote = Quote(ticker=stock.ticker, source_id=self.id,
                          price=float(price_data["lastPrice"]),
                          currency=price_data.get("tradeCurrency") or stock.currency,
                          as_of=str(price_data.get("updatedAt") or ""), url=url)

        sector = company.get("sector") or {}
        info = StockInfo(ticker=stock.ticker, name=company.get("name"),
                         sector=sector.get("sectorname") or None,
                         currency=price_data.get("tradeCurrency"))
        return rec, quote, info
