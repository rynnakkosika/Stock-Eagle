"""Demo source: deterministic sample data, enabled only when FINNHUB_API_KEY is missing.

All rows are clearly labelled DEMO and are NOT real analyst opinions.
"""
from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta

from ..config import Settings
from ..models import Quote, Recommendation, SourceResult, Stock
from ..scale import FINNHUB_FIELDS, weighted_counts
from .base import SourceAdapter

DEMO_URL = "https://example.com/stock-eagle-demo-data"  # reserved example domain, not a source
MONTHS = 6


def _rng(*parts: str) -> random.Random:
    seed = int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:12], 16)
    return random.Random(seed)


class DemoSource(SourceAdapter):
    id = "demo"
    name = "DEMO (esimerkkidata)"
    homepage = DEMO_URL
    description = "Keksittyä esimerkkidataa – ei oikeita suosituksia. Poistuu, kun Finnhub-avain lisätään."
    is_demo = True

    def __init__(self, today: date | None = None):
        self._today = today

    def availability(self, settings: Settings) -> tuple[bool, str]:
        if settings.demo_mode:
            return True, "FINNHUB_API_KEY puuttuu – demotila"
        return False, "Finnhub-avain asetettu – demo pois käytöstä"

    def fetch(self, stocks: list[Stock], settings: Settings) -> SourceResult:
        today = self._today or date.today()
        res = SourceResult(notes=["DEMO: esimerkkidataa, ei oikeita suosituksia"])
        for s in stocks:
            r = _rng("demo", s.ticker)
            price = round(r.uniform(3, 60), 2)
            res.quotes.append(Quote(ticker=s.ticker, source_id=self.id, price=price,
                                    currency=s.currency, as_of=today.isoformat(),
                                    url=DEMO_URL))
            n = r.randint(3, 12)
            bias = r.uniform(-1.5, 1.5)
            target_ratio = 1 + bias * 0.12 + r.uniform(-0.05, 0.05)
            for m in range(MONTHS - 1, -1, -1):
                period = (today.replace(day=1) - timedelta(days=30 * m)).replace(day=1)
                mr = _rng("demo", s.ticker, period.isoformat())
                drift = bias + mr.uniform(-0.8, 0.8)
                counts = {k: 0 for k in FINNHUB_FIELDS}
                for _ in range(n):
                    v = max(1, min(5, round(3 + drift + mr.gauss(0, 0.8))))
                    counts[{5: "strongBuy", 4: "buy", 3: "hold", 2: "sell", 1: "strongSell"}[v]] += 1
                mean, total = weighted_counts(counts)
                tgt = round(price * (target_ratio + (MONTHS - 1 - m) * 0.005), 2)
                res.recommendations.append(Recommendation(
                    source_id=self.id, ticker=s.ticker, analyst="",
                    rating_raw="DEMO " + "/".join(f"{k}:{v}" for k, v in counts.items()),
                    rating=mean, analyst_count=total, target_price=tgt, currency=s.currency,
                    rec_date=period.isoformat(), url=DEMO_URL,
                ))
        return res
