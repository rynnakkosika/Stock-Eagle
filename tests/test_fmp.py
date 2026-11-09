from datetime import date

import pytest

from stock_eagle.config import Settings
from stock_eagle.models import Stock
from stock_eagle.sources.fmp import FmpSource

from .fakes import FakeResponse, FakeSession

KEY = "fmp-test-key-not-real"
GRADES = [{"symbol": "X", "strongBuy": 1, "buy": 5, "hold": 3, "sell": 1, "strongSell": 0,
           "consensus": "Buy"}]
TARGET = [{"symbol": "X", "targetHigh": 12, "targetLow": 8, "targetConsensus": 10.5,
           "targetMedian": 10}]


def adapter(handler):
    sess = FakeSession(handler)
    return FmpSource(session=sess, min_interval=0, sleep=lambda s: None, api_key=KEY,
                     today=date(2026, 11, 9)), sess


def test_availability(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    assert FmpSource().availability(Settings())[0] is False
    monkeypatch.setenv("FMP_API_KEY", "abc")
    assert FmpSource().availability(Settings())[0] is True


def test_candidates():
    a = FmpSource(api_key=KEY)
    assert a.candidates(Stock("NOKIA", "Nokia", ids={"finnhub": "NOK"})) == [
        ("NOKIA.HE", True), ("NOK", False)]
    assert a.candidates(Stock("SAMPO", "Sampo")) == [("SAMPO.HE", True)]
    assert a.candidates(Stock("X", "X", ids={"fmp": "XYZ"})) == [("XYZ", False)]
    assert a.candidates(Stock("AAPL", "Apple", exchange="XNAS")) == [("AAPL", True)]


def test_parse_grades():
    rec = FmpSource(api_key=KEY).parse_grades(Stock("X", "X"), "X.HE", GRADES, "2026-11-09")
    assert rec.analyst_count == 10
    assert rec.rating == pytest.approx((5 + 20 + 9 + 2) / 10)
    assert rec.rating_raw.startswith("Buy (")
    assert rec.rec_date == "2026-11-09"
    assert FmpSource(api_key=KEY).parse_grades(Stock("X", "X"), "X", [], "d") is None
    assert FmpSource(api_key=KEY).parse_grades(Stock("X", "X"), "X", [{"buy": 0}], "d") is None


def test_native_symbol_gets_target():
    def handler(url, params):
        assert params["apikey"] == KEY
        return FakeResponse(200, GRADES if url.endswith("grades-consensus") else TARGET)

    a, _ = adapter(handler)
    res = a.fetch([Stock("NOKIA", "Nokia", ids={"finnhub": "NOK"})], Settings())
    assert len(res.recommendations) == 1
    r = res.recommendations[0]
    assert r.target_price == 10.5 and r.currency == "EUR"
    assert "NOKIA.HE" in r.url and KEY not in r.url


def test_he_denied_falls_back_to_adr_without_target_and_stops_trying_he():
    def handler(url, params):
        if params["symbol"].endswith(".HE"):
            return FakeResponse(402, {"Error Message": "Premium endpoint"})
        assert url.endswith("grades-consensus"), "ADR must not fetch targets"
        return FakeResponse(200, GRADES)

    stocks = [Stock(f"S{i}", f"S{i}", ids={"finnhub": f"S{i}Y"}) for i in range(5)]
    a, sess = adapter(handler)
    res = a.fetch(stocks, Settings())
    assert len(res.recommendations) == 5
    assert all(r.target_price is None for r in res.recommendations)
    he_calls = [p["symbol"] for _, p in sess.calls if p["symbol"].endswith(".HE")]
    assert len(he_calls) == 3  # .HE skipped after 3 denials
    assert any(".HE" in n for n in res.notes)
    assert not res.errors


def test_errors_never_contain_key():
    def handler(url, params):
        raise ConnectionError(f"failed for {url}?apikey={params['apikey']}")

    a, _ = adapter(handler)
    res = a.fetch([Stock("NOKIA", "Nokia")], Settings())
    assert res.errors
    assert all(KEY not in e for e in res.errors)
    assert "***" in res.errors[0]


def test_empty_answer_tries_next_symbol():
    def handler(url, params):
        if params["symbol"] == "NOKIA.HE":
            return FakeResponse(200, [])
        return FakeResponse(200, GRADES)

    a, _ = adapter(handler)
    res = a.fetch([Stock("NOKIA", "Nokia", ids={"finnhub": "NOK"})], Settings())
    assert len(res.recommendations) == 1 and "NOK" in res.recommendations[0].url
