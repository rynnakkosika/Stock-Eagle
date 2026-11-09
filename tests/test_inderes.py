import json

import pytest

from stock_eagle.config import Settings
from stock_eagle.models import Stock
from stock_eagle.sources.inderes import InderesSource, ParseError

from .fakes import FakeResponse, FakeSession

STOCK = Stock("NOKIA", "Nokia", ids={"inderes": "Nokia"})


def page(company: dict) -> str:
    """Synthetic page with the same structure as Inderes' public company page."""
    data = {"props": {"pageProps": {"payload": {"data": {"company": company}}}}}
    return ('<html><body><div id="__next"></div><script id="__NEXT_DATA__" '
            'type="application/json" nonce="x">' + json.dumps(data) + "</script></body></html>")


COMPANY = {
    "name": "Nokia",
    "sector": {"sectorname": "Technology", "industry": "Telecommunications"},
    "analysts": [{"name": "Test Analyst"}],
    "defaultInstrument": {
        "symbol": "NOKIA",
        "estimateData": {
            "researchCurrency": "EUR",
            "estimates": {"date": "2026-10-23T05:56:20.000Z", "recommendation": 2,
                          "targetPrice": 7},
        },
        "priceData": {"tradeCurrency": "EUR", "lastPrice": 7.022,
                      "updatedAt": "2026-11-09T11:42:36.000Z"},
    },
}


def test_parse_page():
    a = InderesSource()
    rec, quote, info = a.parse_page(STOCK, "https://www.inderes.fi/companies/Nokia", page(COMPANY))
    assert rec.rating == 2 and rec.rating_raw == "Vähennä"
    assert rec.target_price == 7 and rec.currency == "EUR"
    assert rec.rec_date == "2026-10-23"
    assert rec.analyst == "Test Analyst" and rec.analyst_count == 1
    assert rec.url == "https://www.inderes.fi/companies/Nokia"
    assert quote.price == pytest.approx(7.022)
    assert info.sector == "Technology"


def test_parse_page_list_shape_and_missing_recommendation():
    c = json.loads(json.dumps(COMPANY))
    c["defaultInstrument"]["estimateData"]["estimates"] = [
        {"date": "2026-01-01", "recommendation": 5, "targetPrice": 9},
        {"date": "2026-03-01", "recommendation": 4, "targetPrice": 8},
    ]
    rec, _, _ = InderesSource().parse_page(STOCK, "u", page(c))
    assert rec.rating == 4 and rec.rec_date == "2026-03-01"

    c["defaultInstrument"]["estimateData"]["estimates"] = {"date": "2026-01-01"}
    rec, quote, _ = InderesSource().parse_page(STOCK, "u", page(c))
    assert rec is None and quote is not None


def test_parse_page_without_data_raises():
    with pytest.raises(ParseError):
        InderesSource().parse_page(STOCK, "u", "<html></html>")
    with pytest.raises(ParseError):
        InderesSource().parse_page(STOCK, "u", page({}).replace('"company": {}', '"x": 1'))


def test_fetch_uses_slug_and_isolates_errors():
    def handler(url, params):
        if url.endswith("/Nokia"):
            return FakeResponse(200, text=page(COMPANY))
        return FakeResponse(404, text="not found")

    sess = FakeSession(handler)
    a = InderesSource(session=sess, min_interval=0, sleep=lambda s: None)
    res = a.fetch([STOCK, Stock("ZZZ", "Zed", ids={"inderes": "Zed"}), Stock("NOID", "No id")],
                  Settings())
    assert len(res.recommendations) == 1
    assert len(res.errors) == 1 and "ZZZ" in res.errors[0]
    assert [u for u, _ in sess.calls] == ["https://www.inderes.fi/companies/Nokia",
                                          "https://www.inderes.fi/companies/Zed"]
    assert "StockEagle" in sess.headers["User-Agent"]


def test_can_be_disabled():
    assert InderesSource().availability(Settings(inderes_enabled=False))[0] is False
