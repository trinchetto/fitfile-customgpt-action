from __future__ import annotations

from collections.abc import Iterator

from fastapi.testclient import TestClient

from fitfile_customgpt_action.app import create_app

from .pytest_types import fixture


@fixture()
def client() -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
