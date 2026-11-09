from stock_eagle.db import Database
from stock_eagle.models import Quote, Stock, StockInfo

from .conftest import rec


def make_db():
    return Database(":memory:")


def test_snapshots_dedupe_and_bump_last_seen():
    db = make_db()
    r = rec(target=10)
    assert db.upsert_recommendations([r], "2026-10-01T00:00:00+00:00") == 1
    r2 = rec(target=10)
    r2.fetched_at = "2026-10-05T00:00:00+00:00"
    assert db.upsert_recommendations([r2]) == 0
    rows = db.recommendations()
    assert len(rows) == 1
    assert rows[0].fetched_at == "2026-10-02T00:00:00+00:00"
    assert rows[0].last_seen_at == "2026-10-05T00:00:00+00:00"


def test_changed_snapshot_is_new_row_and_filters_work():
    db = make_db()
    db.upsert_recommendations([rec(rating=3), rec(rating=4, date="2026-11-01"),
                               rec("BBB", "s2", 2)])
    assert len(db.recommendations()) == 3
    assert len(db.recommendations(sources=["s1"])) == 2
    assert len(db.recommendations(ticker="BBB")) == 1
    assert db.recommendations(sources=[]) == []


def test_null_target_dedupes():
    db = make_db()
    db.upsert_recommendations([rec(target=None)])
    db.upsert_recommendations([rec(target=None)])
    assert len(db.recommendations()) == 1


def test_quotes_upsert_and_filter():
    db = make_db()
    db.upsert_quotes([Quote("AAA", "s1", 10, "EUR", "2026-10-01")])
    db.upsert_quotes([Quote("AAA", "s1", 11, "EUR", "2026-10-02")])
    db.upsert_quotes([Quote("AAA", "s2", 12, "EUR", "2026-10-02")])
    assert sorted(q.price for q in db.quotes()) == [11, 12]
    assert [q.price for q in db.quotes(sources=["s2"])] == [12]


def test_stocks_sync_and_info_fill():
    db = make_db()
    db.sync_stocks([Stock("AAA", "Alpha", sector="Tech"), Stock("BBB", "BBB")])
    db.update_stock_info([StockInfo("AAA", sector="Other"), StockInfo("BBB", name="Beta",
                                                                      sector="Energy")])
    s = {r["ticker"]: r for r in db.stocks()}
    assert s["AAA"]["sector"] == "Tech"  # watchlist wins
    assert s["BBB"]["sector"] == "Energy" and s["BBB"]["name"] == "Beta"


def test_fetch_runs():
    db = make_db()
    rid = db.start_run("s1")
    db.finish_run(rid, "ok", "", 3)
    rid2 = db.start_run("s1")
    db.finish_run(rid2, "error", "boom")
    runs = db.last_runs()
    assert runs["s1"]["status"] == "error" and runs["s1"]["message"] == "boom"
