from __future__ import annotations

import types
from collections.abc import Iterator
from typing import Any, cast

import pytest

from fitfile_customgpt_action import message_registry

from .pytest_types import fixture, parametrize


@fixture(autouse=True)
def clear_registry_cache() -> Iterator[None]:
    message_registry._registry.cache_clear()
    yield
    message_registry._registry.cache_clear()


@parametrize("message_name", ["file_id", "record", "sport"])
def test_resolve_known_messages(message_name: str) -> None:
    message_cls = message_registry.resolve(message_name)
    assert message_cls.NAME.lower() == message_name


def test_resolve_unknown_message() -> None:
    with pytest.raises(KeyError):
        message_registry.resolve("totally-unknown")


def test_build_registry_without_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_package = types.SimpleNamespace(__path__=["/tmp/fake"])

    def fake_import(name: str) -> types.SimpleNamespace:
        if name == message_registry.PACKAGE_NAME:
            return fake_package
        raise AssertionError(f"Unexpected import: {name}")

    registry_module = cast(Any, message_registry)
    monkeypatch.setattr(registry_module.importlib, "import_module", fake_import)
    monkeypatch.setattr(
        registry_module.pkgutil,
        "iter_modules",
        lambda _path: iter(()),
    )

    with pytest.raises(RuntimeError, match="No FIT message definitions"):
        message_registry._build_registry()
