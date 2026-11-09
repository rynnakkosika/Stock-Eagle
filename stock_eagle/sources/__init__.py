"""Source registry: every module in this package that defines a SourceAdapter subclass is
picked up automatically. Adding a source = adding one module here, nothing else."""
from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil

from .base import SourceAdapter

log = logging.getLogger(__name__)


def discover() -> list[SourceAdapter]:
    """Import all modules of this package and instantiate concrete SourceAdapter subclasses."""
    adapters: dict[str, SourceAdapter] = {}
    for mod_info in pkgutil.iter_modules(__path__):
        if mod_info.name.startswith("_") or mod_info.name == "base":
            continue
        try:
            module = importlib.import_module(f"{__name__}.{mod_info.name}")
        except Exception:  # a broken source must not break the app
            log.exception("Failed to import source module %s", mod_info.name)
            continue
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, SourceAdapter) and obj is not SourceAdapter
                    and not inspect.isabstract(obj) and obj.__module__ == module.__name__):
                inst = obj()
                if not inst.id:
                    log.warning("Source %s has no id, skipped", obj.__name__)
                    continue
                if inst.id in adapters:
                    log.warning("Duplicate source id %s, skipped %s", inst.id, obj.__name__)
                    continue
                adapters[inst.id] = inst
    return sorted(adapters.values(), key=lambda a: a.id)


__all__ = ["SourceAdapter", "discover"]
