import pytest

from stock_eagle import consensus as C
from stock_eagle.models import Quote

from .conftest import rec

STOCKS = [
    {"ticker": "AAA", "name": "Alpha", "sector": "Tech", "currency": "EUR"},
    {"ticker": "BBB", "name": "Beta", "sector": "Energy", "currency": "EUR"},
    {"ticker": "CCC", "name": "Gamma", "sector": "Tech", "currency": "EUR"},
]


def q(ticker, price, ccy="EUR", src="s1", as_of="2026-10-05"):
    return Quote(ticker=ticker, source_id=src, price=price, currency=ccy, as_of=as_of,
                 fetched_at=as_of)


def test_latest_per_key_keeps_newest():
    old = rec(rating=2, date="2026-09-01")
    new = rec(rating=4, date="2026-10-01")
    other_analyst = rec(rating=5, date="2026-08-01", analyst="X")
    out = C.latest_per_key([new, old, other_analyst])
    assert sorted(r.rating for r in out) == [4, 5]


def test_weighted_consensus_weights_by_analyst_count():
    # aggregate source: 9 analysts at 4.0, single analyst at 1.0 → (36 + 1) / 10
    cons, n = C.weighted_consensus([rec(rating=4.0, n=9), rec(rating=1.0, source="s2")])
    assert n == 10
    assert cons == pytest.approx(3.7)


def test_weighted_consensus_empty():
    assert C.weighted_consensus([]) == (None, 0)


def test_average_target_filters_currency_and_weights():
    recs = [rec(target=10, n=3), rec(target=20, n=1, source="s2"),
            rec(target=999, ccy="USD", source="s3")]
    assert C.average_target(recs, "EUR") == pytest.approx(12.5)
    assert C.average_target([rec(target=None)], "EUR") is None
    assert C.average_target(recs, None) is None  # mixed currencies, no reference
    assert C.average_target([rec(target=5), rec(target=7, source="s2")], None) == 6


def test_upside():
    assert C.upside(12, 10) == pytest.approx(0.2)
    assert C.upside(8, 10) == pytest.approx(-0.2)
    assert C.upside(None, 10) is None
    assert C.upside(10, None) is None
    assert C.upside(10, 0) is None


def test_pick_quote_prefers_currency_then_newest():
    qs = [q("AAA", 1, "USD", as_of="2026-10-09"), q("AAA", 2, as_of="2026-10-01"),
          q("AAA", 3, as_of="2026-10-03", src="s2")]
    assert C.pick_quote(qs, "EUR").price == 3
    assert C.pick_quote([], "EUR") is None
    assert C.pick_quote(qs[:1], "EUR").price == 1  # fallback to other currency


def test_build_rows_full():
    recs = [
        rec("AAA", "s1", 5, n=2, target=12, date="2026-10-01"),
        rec("AAA", "s2", 3, target=9, date="2026-10-03", analyst="Ann"),
        rec("BBB", "s1", 2, target=8, date="2026-09-01"),
        rec("CCC", "s1", 4),
    ]
    rows = {r.ticker: r for r in C.build_rows(recs, [q("AAA", 10), q("BBB", 10)], STOCKS)}
    a = rows["AAA"]
    assert a.consensus == pytest.approx(13 / 3)
    assert a.label == "Lisää"
    assert a.n_recommendations == 3
    assert a.avg_target == pytest.approx(11)
    assert a.upside == pytest.approx(0.1)
    assert a.latest_date == "2026-10-03"
    assert a.sources == ["s1", "s2"]
    assert rows["BBB"].upside == pytest.approx(-0.2)
    assert rows["CCC"].price is None and rows["CCC"].upside is None


def test_sort_by_upside_missing_last():
    recs = [rec("AAA", target=11), rec("BBB", target=15), rec("CCC", target=20)]
    rows = C.build_rows(recs, [q("AAA", 10), q("BBB", 10)], STOCKS)
    assert [r.ticker for r in C.sort_rows(rows, "upside")] == ["BBB", "AAA", "CCC"]


def test_sort_by_consensus_and_tiebreak():
    recs = [rec("AAA", rating=4), rec("BBB", rating=4, n=5), rec("CCC", rating=5)]
    rows = C.build_rows(recs, [], STOCKS)
    assert [r.ticker for r in C.sort_rows(rows, "consensus")] == ["CCC", "BBB", "AAA"]


def test_sort_by_freshness():
    recs = [rec("AAA", date="2026-01-01"), rec("BBB", date="2026-11-01"),
            rec("CCC", date="2026-06-01")]
    rows = C.build_rows(recs, [], STOCKS)
    assert [r.ticker for r in C.sort_rows(rows, "freshness")] == ["BBB", "CCC", "AAA"]


def test_sort_unknown_key():
    with pytest.raises(ValueError):
        C.sort_rows([], "nope")


def test_filters():
    recs = [rec("AAA", rating=5), rec("BBB", rating=3), rec("CCC", rating=3)]
    rows = C.build_rows(recs, [], STOCKS)
    assert {r.ticker for r in C.filter_rows(rows, labels=["Pidä"])} == {"BBB", "CCC"}
    assert {r.ticker for r in C.filter_rows(rows, sectors=["Tech"])} == {"AAA", "CCC"}
    assert {r.ticker for r in C.filter_rows(rows, labels=["Pidä"], sectors=["Tech"])} == {"CCC"}
    assert len(C.filter_rows(rows)) == 3


def test_source_filter_restricts_consensus():
    recs = [rec("AAA", "s1", 5), rec("AAA", "s2", 1)]
    only_s2 = [r for r in recs if r.source_id == "s2"]
    rows = C.build_rows(only_s2, [], STOCKS)
    assert rows[0].consensus == 1 and rows[0].label == "Myy"
