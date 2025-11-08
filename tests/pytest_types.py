from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

import pytest

F = TypeVar("F", bound=Callable[..., object])


def fixture(*args: Any, **kwargs: Any) -> Callable[[F], F]:
    return cast(Callable[[F], F], pytest.fixture(*args, **kwargs))


def parametrize(*args: Any, **kwargs: Any) -> Callable[[F], F]:
    return cast(Callable[[F], F], pytest.mark.parametrize(*args, **kwargs))
