"""Configuration: .env loading, paths and the watchlist."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .models import Stock

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "stock_eagle.db"
DEFAULT_WATCHLIST = ROOT / "config" / "watchlist.toml"


def _truthy(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", "ei"}


@dataclass(frozen=True)
class Settings:
    finnhub_api_key: str | None = None
    inderes_enabled: bool = True
    db_path: Path = DEFAULT_DB
    watchlist_path: Path = DEFAULT_WATCHLIST
    http_timeout: float = 20.0

    @property
    def demo_mode(self) -> bool:
        return not self.finnhub_api_key


def load_settings(env_file: Path | None = None) -> Settings:
    """Read settings from environment variables, after loading .env (if present).

    Values already in the process environment win over .env.
    """
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file or ROOT / ".env", override=False)
    except ImportError:  # pragma: no cover - dotenv is a hard dependency
        pass
    key = (os.environ.get("FINNHUB_API_KEY") or "").strip() or None
    db = os.environ.get("STOCK_EAGLE_DB")
    wl = os.environ.get("STOCK_EAGLE_WATCHLIST")
    return Settings(
        finnhub_api_key=key,
        inderes_enabled=_truthy(os.environ.get("INDERES_ENABLED"), True),
        db_path=Path(db) if db else DEFAULT_DB,
        watchlist_path=Path(wl) if wl else DEFAULT_WATCHLIST,
    )


def load_watchlist(path: Path) -> list[Stock]:
    """Parse watchlist.toml → list of Stock.

    Format::

        [[stocks]]
        ticker = "NOKIA"
        name = "Nokia"
        sector = "Teknologia"
        ids = { finnhub = "NOKIA.HE", inderes = "Nokia" }
    """
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    stocks: list[Stock] = []
    seen: set[str] = set()
    for entry in data.get("stocks", []):
        ticker = str(entry["ticker"]).strip().upper()
        if ticker in seen:
            raise ValueError(f"duplicate ticker in watchlist: {ticker}")
        seen.add(ticker)
        stocks.append(
            Stock(
                ticker=ticker,
                name=str(entry.get("name", ticker)),
                sector=str(entry.get("sector", "")),
                exchange=str(entry.get("exchange", "XHEL")),
                currency=str(entry.get("currency", "EUR")),
                ids={str(k): str(v) for k, v in (entry.get("ids") or {}).items()},
            )
        )
    return stocks
