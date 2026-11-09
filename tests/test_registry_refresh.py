from datetime import date

from stock_eagle.changes import detect_changes
from stock_eagle.config import Settings, load_watchlist, DEFAULT_WATCHLIST
from stock_eagle.db import Database
from stock_eagle.models import Recommendation, SourceResult, Stock
from stock_eagle.refresh import enabled_sources, refresh_all
from stock_eagle.sources import SourceAdapter, discover
from stock_eagle.sources.demo import DemoSource


class GoodSource(SourceAdapter):
    id = "good"
    name = "Good"

    def availability(self, settings):
        return True, ""

    def fetch(self, stocks, settings):
        return SourceResult(recommendations=[Recommendation(
            source_id=self.id, ticker=s.ticker, rating_raw="Osta", rating=5,
            rec_date="2026-10-01", url="https://example.com") for s in stocks])


class BrokenSource(GoodSource):
    id = "broken"

    def fetch(self, stocks, settings):
        raise RuntimeError("down")


class OffSource(GoodSource):
    id = "off"

    def availability(self, settings):
        return False, "no key"


def test_discover_finds_all_builtin_sources():
    ids = [a.id for a in discover()]
    assert ids == ["demo", "finnhub", "inderes"]


def test_demo_only_without_key():
    no_key = {a.id for a in enabled_sources(Settings(inderes_enabled=False))}
    with_key = {a.id for a in enabled_sources(Settings(finnhub_api_key="k",
                                                       inderes_enabled=False))}
    assert no_key == {"demo"}
    assert with_key == {"finnhub"}


def test_refresh_isolates_failures():
    db = Database(":memory:")
    stocks = [Stock("AAA", "A"), Stock("BBB", "B")]
    reports = refresh_all(db, stocks, Settings(), adapters=[BrokenSource(), GoodSource(),
                                                           OffSource()])
    status = {r.source_id: r.status for r in reports}
    assert status == {"broken": "error", "good": "ok", "off": "skipped"}
    assert len(db.recommendations()) == 2
    runs = db.last_runs()
    assert runs["broken"]["status"] == "error" and "down" in runs["broken"]["message"]
    assert "off" not in runs


def test_refresh_twice_does_not_duplicate():
    db = Database(":memory:")
    stocks = [Stock("AAA", "A")]
    refresh_all(db, stocks, Settings(), adapters=[GoodSource()])
    refresh_all(db, stocks, Settings(), adapters=[GoodSource()])
    assert len(db.recommendations()) == 1


def test_demo_source_produces_history_and_changes():
    stocks = load_watchlist(DEFAULT_WATCHLIST)[:10]
    res = DemoSource(today=date(2026, 11, 9)).fetch(stocks, Settings())
    assert len(res.quotes) == 10
    assert all(r.url.startswith("https://example.com") for r in res.recommendations)
    assert all(1 <= r.rating <= 5 for r in res.recommendations)
    assert detect_changes(res.recommendations)  # demo history contains changes
    # deterministic
    again = DemoSource(today=date(2026, 11, 9)).fetch(stocks, Settings())
    assert [r.rating for r in again.recommendations] == [r.rating for r in res.recommendations]


def test_watchlist_loads():
    stocks = load_watchlist(DEFAULT_WATCHLIST)
    assert len(stocks) >= 40
    assert len({s.ticker for s in stocks}) == len(stocks)
    assert all(s.ids.get("inderes") for s in stocks)
