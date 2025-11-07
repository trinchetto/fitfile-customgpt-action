from __future__ import annotations

import importlib
import inspect
import pkgutil
from functools import lru_cache

from fit_tool.data_message import DataMessage

PACKAGE_NAME = "fit_tool.profile.messages"


def _is_message_class(candidate: type, module_name: str) -> bool:
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
    return _build_registry()


def resolve(message_name: str) -> type[DataMessage]:
    normalized = message_name.strip().lower()
    mapping = _registry()
    if normalized not in mapping:
        raise KeyError(f"Unknown FIT message '{message_name}'.")
    return mapping[normalized]
