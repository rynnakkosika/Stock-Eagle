"""Refresh orchestration: run every enabled adapter, store results, record fetch runs."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from .config import Settings
from .db import Database, utcnow
from .models import Stock
from .sources import SourceAdapter, discover

log = logging.getLogger(__name__)


@dataclass
class RunReport:
    source_id: str
    status: str  # ok | partial | error | skipped
    message: str
    n_records: int = 0


def enabled_sources(settings: Settings, adapters: list[SourceAdapter] | None = None
                    ) -> list[SourceAdapter]:
    adapters = adapters if adapters is not None else discover()
    return [a for a in adapters if a.availability(settings)[0]]


def refresh_all(db: Database, stocks: list[Stock], settings: Settings,
                adapters: list[SourceAdapter] | None = None,
                progress: Callable[[str], None] | None = None) -> list[RunReport]:
    adapters = adapters if adapters is not None else discover()
    db.sync_stocks(stocks)
    reports: list[RunReport] = []
    for adapter in adapters:
        enabled, reason = adapter.availability(settings)
        if not enabled:
            reports.append(RunReport(adapter.id, "skipped", reason))
            continue
        if progress:
            progress(f"Haetaan: {adapter.name} …")
        run_id = db.start_run(adapter.id)
        fetched_at = utcnow()
        try:
            result = adapter.fetch(stocks, settings)
        except Exception as exc:  # adapter bug or total outage – isolate it
            log.exception("Source %s failed", adapter.id)
            msg = f"{type(exc).__name__}: {exc}"
            db.finish_run(run_id, "error", msg)
            reports.append(RunReport(adapter.id, "error", msg))
            continue
        for r in result.recommendations:
            r.fetched_at = r.fetched_at or fetched_at
        for q in result.quotes:
            q.fetched_at = q.fetched_at or fetched_at
        db.upsert_recommendations(result.recommendations, fetched_at)
        db.upsert_quotes(result.quotes, fetched_at)
        db.update_stock_info(result.stock_info)
        n = len(result.recommendations)
        if result.errors and n == 0 and not result.quotes:
            status = "error"
        elif result.errors:
            status = "partial"
        else:
            status = "ok"
        parts = result.notes + result.errors[:5]
        if len(result.errors) > 5:
            parts.append(f"… ja {len(result.errors) - 5} muuta virhettä")
        msg = "; ".join(parts)
        db.finish_run(run_id, status, msg, n)
        reports.append(RunReport(adapter.id, status, msg, n))
    return reports
