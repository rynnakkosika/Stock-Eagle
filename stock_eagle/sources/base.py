"""Source adapter contract. See specs/001-analyst-consensus/contracts/source-adapter.md."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod

from ..config import Settings
from ..models import SourceResult, Stock

USER_AGENT = "StockEagle/0.1 (personal, non-commercial use; low-frequency manual refresh)"


class SourceAdapter(ABC):
    """Base class for a data source. Subclasses are discovered automatically."""

    id: str = ""
    name: str = ""
    homepage: str = ""
    #: Short description shown in the UI (e.g. data terms / limitations).
    description: str = ""
    #: Demo sources are clearly labelled in the UI.
    is_demo: bool = False

    @abstractmethod
    def availability(self, settings: Settings) -> tuple[bool, str]:
        """Return (enabled, reason)."""

    @abstractmethod
    def fetch(self, stocks: list[Stock], settings: Settings) -> SourceResult:
        """Fetch data for the given stocks. Must not raise for single-stock failures."""

    def default_symbol(self, stock: Stock) -> str | None:
        """Source-specific identifier when the watchlist has none. Override if derivable."""
        return None

    def symbol_for(self, stock: Stock) -> str | None:
        return stock.ids.get(self.id) or self.default_symbol(stock)


class RateLimiter:
    """Ensures a minimum interval between calls (polite crawling / API quotas)."""

    def __init__(self, min_interval: float, sleep=time.sleep, clock=time.monotonic):
        self.min_interval = min_interval
        self._sleep = sleep
        self._clock = clock
        self._last: float | None = None

    def wait(self) -> None:
        if self._last is not None:
            delta = self._clock() - self._last
            if delta < self.min_interval:
                self._sleep(self.min_interval - delta)
        self._last = self._clock()
