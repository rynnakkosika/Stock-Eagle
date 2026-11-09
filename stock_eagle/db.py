"""SQLite storage and cache."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .models import Quote, Recommendation, Stock, StockInfo

SCHEMA = """
CREATE TABLE IF NOT EXISTS stocks (
    ticker   TEXT PRIMARY KEY,
    name     TEXT NOT NULL,
    sector   TEXT NOT NULL DEFAULT '',
    exchange TEXT NOT NULL DEFAULT '',
    currency TEXT NOT NULL DEFAULT 'EUR'
);
CREATE TABLE IF NOT EXISTS recommendations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint   TEXT NOT NULL UNIQUE,
    source_id     TEXT NOT NULL,
    ticker        TEXT NOT NULL,
    analyst       TEXT NOT NULL DEFAULT '',
    rating_raw    TEXT NOT NULL,
    rating        REAL NOT NULL,
    analyst_count INTEGER NOT NULL DEFAULT 1,
    target_price  REAL,
    currency      TEXT,
    rec_date      TEXT NOT NULL,
    url           TEXT NOT NULL,
    fetched_at    TEXT NOT NULL,
    last_seen_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_rec_ticker ON recommendations(ticker, source_id, analyst, rec_date);
CREATE TABLE IF NOT EXISTS quotes (
    ticker     TEXT NOT NULL,
    source_id  TEXT NOT NULL,
    price      REAL NOT NULL,
    currency   TEXT NOT NULL,
    as_of      TEXT NOT NULL,
    url        TEXT NOT NULL DEFAULT '',
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (ticker, source_id)
);
CREATE TABLE IF NOT EXISTS fetch_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT NOT NULL,
    message     TEXT NOT NULL DEFAULT '',
    n_records   INTEGER NOT NULL DEFAULT 0
);
"""


def utcnow() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def fingerprint(rec: Recommendation) -> str:
    target = "" if rec.target_price is None else f"{rec.target_price:.4f}"
    return "|".join(
        [rec.source_id, rec.ticker, rec.analyst, rec.rec_date, rec.rating_raw, f"{rec.rating:.4f}",
         str(rec.analyst_count), target]
    )


class Database:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def tx(self):
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    # ---- stocks -------------------------------------------------------------------------
    def sync_stocks(self, stocks: Iterable[Stock]) -> None:
        """Insert watchlist stocks; keep sector/name learned from sources if watchlist is empty."""
        with self.tx() as c:
            for s in stocks:
                c.execute(
                    """INSERT INTO stocks(ticker, name, sector, exchange, currency)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(ticker) DO UPDATE SET
                         name = excluded.name,
                         sector = CASE WHEN excluded.sector != '' THEN excluded.sector
                                       ELSE stocks.sector END,
                         exchange = excluded.exchange,
                         currency = excluded.currency""",
                    (s.ticker, s.name, s.sector, s.exchange, s.currency),
                )

    def update_stock_info(self, infos: Iterable[StockInfo]) -> None:
        """Fill in missing name/sector from source metadata (watchlist values win)."""
        with self.tx() as c:
            for i in infos:
                if i.sector:
                    c.execute("UPDATE stocks SET sector = ? WHERE ticker = ? AND sector = ''",
                              (i.sector, i.ticker))
                if i.name:
                    c.execute("UPDATE stocks SET name = ? WHERE ticker = ? AND name = ticker",
                              (i.name, i.ticker))

    def stocks(self) -> list[dict]:
        return [dict(r) for r in self._conn.execute("SELECT * FROM stocks ORDER BY name")]

    # ---- recommendations ----------------------------------------------------------------
    def upsert_recommendations(self, recs: Iterable[Recommendation], fetched_at: str | None = None
                               ) -> int:
        """Store snapshots. Identical snapshots only bump last_seen_at. Returns #new rows."""
        now = fetched_at or utcnow()
        new = 0
        with self.tx() as c:
            for r in recs:
                fp = fingerprint(r)
                seen = r.fetched_at or now
                exists = c.execute(
                    "SELECT 1 FROM recommendations WHERE fingerprint = ?", (fp,)
                ).fetchone()
                if exists:
                    c.execute(
                        "UPDATE recommendations SET last_seen_at = ?, url = ? WHERE fingerprint = ?",
                        (seen, r.url, fp),
                    )
                    continue
                c.execute(
                    """INSERT INTO recommendations(fingerprint, source_id, ticker, analyst, rating_raw,
                         rating, analyst_count, target_price, currency, rec_date, url, fetched_at,
                         last_seen_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (fp, r.source_id, r.ticker, r.analyst, r.rating_raw, r.rating, r.analyst_count,
                     r.target_price, r.currency, r.rec_date, r.url, seen, seen),
                )
                new += 1
        return new

    def recommendations(self, sources: Iterable[str] | None = None, ticker: str | None = None
                        ) -> list[Recommendation]:
        sql = "SELECT * FROM recommendations WHERE 1=1"
        args: list = []
        if sources is not None:
            src = list(sources)
            if not src:
                return []
            sql += f" AND source_id IN ({','.join('?' * len(src))})"
            args += src
        if ticker:
            sql += " AND ticker = ?"
            args.append(ticker)
        sql += " ORDER BY ticker, source_id, analyst, rec_date, fetched_at, id"
        out = []
        for row in self._conn.execute(sql, args):
            d = dict(row)
            d.pop("id")
            d.pop("fingerprint")
            out.append(Recommendation(**d))
        return out

    # ---- quotes -------------------------------------------------------------------------
    def upsert_quotes(self, quotes: Iterable[Quote], fetched_at: str | None = None) -> None:
        now = fetched_at or utcnow()
        with self.tx() as c:
            for q in quotes:
                c.execute(
                    """INSERT INTO quotes(ticker, source_id, price, currency, as_of, url, fetched_at)
                       VALUES (?,?,?,?,?,?,?)
                       ON CONFLICT(ticker, source_id) DO UPDATE SET price = excluded.price,
                         currency = excluded.currency, as_of = excluded.as_of, url = excluded.url,
                         fetched_at = excluded.fetched_at""",
                    (q.ticker, q.source_id, q.price, q.currency, q.as_of, q.url, q.fetched_at or now),
                )

    def quotes(self, sources: Iterable[str] | None = None) -> list[Quote]:
        rows = [dict(r) for r in self._conn.execute("SELECT * FROM quotes")]
        if sources is not None:
            allowed = set(sources)
            rows = [r for r in rows if r["source_id"] in allowed]
        return [Quote(**r) for r in rows]

    # ---- fetch runs ---------------------------------------------------------------------
    def start_run(self, source_id: str) -> int:
        with self.tx() as c:
            cur = c.execute(
                "INSERT INTO fetch_runs(source_id, started_at, status) VALUES (?, ?, 'running')",
                (source_id, utcnow()),
            )
            return int(cur.lastrowid)

    def finish_run(self, run_id: int, status: str, message: str = "", n_records: int = 0) -> None:
        with self.tx() as c:
            c.execute(
                "UPDATE fetch_runs SET finished_at = ?, status = ?, message = ?, n_records = ? "
                "WHERE id = ?",
                (utcnow(), status, message, n_records, run_id),
            )

    def last_runs(self) -> dict[str, dict]:
        """Latest finished run per source."""
        rows = self._conn.execute(
            """SELECT f.* FROM fetch_runs f
               JOIN (SELECT source_id, MAX(id) AS mid FROM fetch_runs
                     WHERE finished_at IS NOT NULL GROUP BY source_id) m ON f.id = m.mid"""
        )
        return {r["source_id"]: dict(r) for r in rows}
