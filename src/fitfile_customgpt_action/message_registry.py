"""Discover and cache FIT `DataMessage` subclasses exposed by `fit_tool`."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from functools import lru_cache

from fit_tool.data_message import DataMessage

PACKAGE_NAME = "fit_tool.profile.messages"


def _is_message_class(candidate: type, module_name: str) -> bool:
    """Return True when `candidate` is a concrete message defined in `module_name`."""
    if candidate is DataMessage:
        return False

    if not inspect.isclass(candidate):
        return False

    if not issubclass(candidate, DataMessage):
        return False

    if candidate.__module__ != module_name:
        return False

    if not hasattr(candidate, "NAME"):
        return False

    return bool(candidate.NAME)


def _build_registry() -> dict[str, type[DataMessage]]:
    """Scan the fit_tool profile package and collect every named DataMessage subclass."""
    package = importlib.import_module(PACKAGE_NAME)
    registry: dict[str, type[DataMessage]] = {}

    for module_info in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{PACKAGE_NAME}.{module_info.name}")
        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if not _is_message_class(candidate, module.__name__):
                continue

            name = candidate.NAME.lower()
            registry[name] = candidate

    if not registry:
        raise RuntimeError("No FIT message definitions were discovered.")

    return registry


@lru_cache(maxsize=1)
def _registry() -> dict[str, type[DataMessage]]:
    """Memoized accessor for the discovered message registry."""
    return _build_registry()


def resolve(message_name: str) -> type[DataMessage]:
    """Look up a DataMessage subclass by name, raising KeyError when unknown."""
    normalized = message_name.strip().lower()
    mapping = _registry()
    if normalized not in mapping:
        raise KeyError(f"Unknown FIT message '{message_name}'.")
    return mapping[normalized]
