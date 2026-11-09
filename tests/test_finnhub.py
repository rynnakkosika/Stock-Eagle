import pytest

from stock_eagle.config import Settings
from stock_eagle.models import Stock
from stock_eagle.sources.finnhub import FinnhubSource

from .fakes import FakeResponse, FakeSession

SETTINGS = Settings(finnhub_api_key="test-key-not-real")
NOKIA = Stock("NOKIA", "Nokia", sector="Tech", ids={"finnhub": "NOKIA.HE"})
TRENDS = [
    {"period": "2026-10-01", "strongBuy": 2, "buy": 4, "hold": 3, "sell": 1, "strongSell": 0,
     "symbol": "NOKIA.HE"},
    {"period": "2026-09-01", "strongBuy": 1, "buy": 3, "hold": 5, "sell": 1, "strongSell": 0,
     "symbol": "NOKIA.HE"},
]


def adapter(handler):
    sess = FakeSession(handler)
    return FinnhubSource(session=sess, min_interval=0, sleep=lambda s: None), sess


def test_availability_requires_key():
    assert FinnhubSource().availability(Settings())[0] is False
    assert FinnhubSource().availability(SETTINGS)[0] is True


def test_symbol_resolution():
    # Helsinki stocks need an explicit mapping (free tier denies .HE symbols)
    assert FinnhubSource().symbol_for(Stock("SAMPO", "Sampo")) is None
    assert FinnhubSource().symbol_for(Stock("NOKIA", "Nokia", ids={"finnhub": "NOK"})) == "NOK"
    assert FinnhubSource().symbol_for(Stock("AAPL", "Apple", exchange="XNAS")) == "AAPL"


def test_is_native():
    assert FinnhubSource.is_native(NOKIA, "NOKIA.HE")
    assert not FinnhubSource.is_native(NOKIA, "NOK")
    assert FinnhubSource.is_native(Stock("AAPL", "Apple", exchange="XNAS"), "AAPL")


def test_adr_mapping_fetches_recommendations_only():
    def handler(url, params):
        assert url.endswith("/stock/recommendation"), url
        return FakeResponse(200, TRENDS)

    a, sess = adapter(handler)
    res = a.fetch([Stock("NOKIA", "Nokia", ids={"finnhub": "NOK"}), Stock("SAMPO", "Sampo")],
                  SETTINGS)
    assert len(res.recommendations) == 2 and not res.quotes and not res.errors
    assert [p["symbol"] for _, p in sess.calls] == ["NOK"]  # SAMPO has no mapping → no call


def test_parse_trends():
    recs = FinnhubSource().parse_trends("NOKIA", "NOKIA.HE", TRENDS)
    assert [r.rec_date for r in recs] == ["2026-09-01", "2026-10-01"]
    latest = recs[-1]
    assert latest.analyst_count == 10
    assert latest.rating == pytest.approx((2 * 5 + 4 * 4 + 3 * 3 + 1 * 2) / 10)
    assert latest.url.startswith("https://finnhub.io/")
    assert "test-key" not in latest.url


def test_parse_trends_skips_empty_period():
    assert FinnhubSource().parse_trends("X", "X", [{"period": "2026-01-01"}]) == []


def test_fetch_happy_path_with_target():
    def handler(url, params):
        if url.endswith("/stock/recommendation"):
            return FakeResponse(200, TRENDS)
        if url.endswith("/quote"):
            return FakeResponse(200, {"c": 7.0, "t": 1762700000})
        if url.endswith("/stock/price-target"):
            return FakeResponse(200, {"targetMean": 8.4, "lastUpdated": "2026-10-15 00:00:00"})
        raise AssertionError(url)

    a, sess = adapter(handler)
    res = a.fetch([NOKIA], SETTINGS)
    assert not res.errors
    assert sess.headers["X-Finnhub-Token"] == "test-key-not-real"
    assert all("token" not in p for _, p in sess.calls)  # key never in URL params
    assert len(res.recommendations) == 2
    latest = max(res.recommendations, key=lambda r: r.rec_date)
    assert latest.target_price == 8.4 and latest.rec_date == "2026-10-15"
    assert res.quotes[0].price == 7.0 and res.quotes[0].currency == "EUR"


def test_fetch_premium_endpoint_denied_is_graceful():
    def handler(url, params):
        if url.endswith("/stock/price-target"):
            return FakeResponse(403, {"error": "You don't have access to this resource."})
        if url.endswith("/stock/recommendation"):
            return FakeResponse(200, TRENDS)
        return FakeResponse(200, {"c": 7.0, "t": 0})

    stocks = [Stock(f"S{i}", f"S{i}", sector="x", exchange="XNAS") for i in range(5)]
    a, sess = adapter(handler)
    res = a.fetch(stocks, SETTINGS)
    assert len(res.recommendations) == 10
    assert not res.errors  # price-target denial is summarised in notes, not per stock
    assert any("price-target" in n for n in res.notes)
    pt_calls = [u for u, _ in sess.calls if u.endswith("price-target")]
    assert len(pt_calls) == 3  # stops after 3 consecutive denials


def test_fetch_international_denied_reports_errors():
    a, _ = adapter(lambda url, params: FakeResponse(403, {"error": "denied"}))
    res = a.fetch([NOKIA], SETTINGS)
    assert res.recommendations == [] and res.errors


def test_fetch_network_error_isolated_per_stock():
    def handler(url, params):
        if params["symbol"] == "BAD.HE":
            raise ConnectionError("boom")
        if url.endswith("/stock/recommendation"):
            return FakeResponse(200, TRENDS)
        return FakeResponse(200, {})

    a, _ = adapter(handler)
    res = a.fetch([Stock("BAD", "Bad", sector="x", ids={"finnhub": "BAD.HE"}), NOKIA], SETTINGS)
    assert len(res.recommendations) == 2
    assert any("BAD.HE" in e for e in res.errors)
