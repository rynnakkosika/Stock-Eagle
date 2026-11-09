import socket

import pytest

from stock_eagle.models import Recommendation


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Constitution VII: tests must not hit the network."""

    def guard(*args, **kwargs):
        raise RuntimeError("network access in tests is not allowed")

    monkeypatch.setattr(socket, "create_connection", guard)
    monkeypatch.setattr(socket.socket, "connect", guard)


def rec(ticker="AAA", source="s1", rating=3.0, date="2026-10-01", analyst="", n=1, target=None,
        ccy="EUR", fetched="2026-10-02T00:00:00+00:00", raw=None):
    return Recommendation(
        source_id=source, ticker=ticker, analyst=analyst, rating_raw=raw or str(rating),
        rating=rating, analyst_count=n, target_price=target, currency=ccy, rec_date=date,
        url=f"https://example.com/{source}/{ticker}", fetched_at=fetched, last_seen_at=fetched,
    )
