from __future__ import annotations

import json
from pathlib import Path
from typing import Any, BinaryIO
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from fitfile_customgpt_action import client


def test_parse_fit_posts_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    fit_path = tmp_path / "sample.fit"
    fit_path.write_bytes(b"payload")

    expected = {"status": "ok"}
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = expected

    def fake_post(
        url: str,
        files: dict[str, tuple[str, BinaryIO, str]],
        timeout: float,
    ) -> MagicMock:
        assert url == "http://example.com/fit/parse"
        assert timeout == 30.0
        assert "file" in files
        filename, handle, mimetype = files["file"]
        assert filename == fit_path.name
        assert mimetype == "application/octet-stream"
        assert handle.read() == b"payload"
        handle.seek(0)
        return mock_response

    monkeypatch.setattr("fitfile_customgpt_action.client.httpx.post", fake_post)

    result = client.parse_fit("http://example.com", fit_path)
    assert result == expected


def test_produce_fit_posts_payload(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    payload_path = tmp_path / "payload.json"
    payload: dict[str, list[Any]] = {"messages": []}
    payload_path.write_text(json.dumps(payload))

    output_path = tmp_path / "out.fit"
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.content = b"fit-bytes"

    def fake_post(
        url: str,
        json: dict[str, list[Any]],
        timeout: float,
    ) -> MagicMock:
        assert url == "http://example.com/fit/produce"
        assert json == payload
        assert timeout == 30.0
        return mock_response

    monkeypatch.setattr("fitfile_customgpt_action.client.httpx.post", fake_post)

    result_path = client.produce_fit("http://example.com", payload_path, output_path)
    assert result_path == output_path
    assert output_path.read_bytes() == b"fit-bytes"


@pytest.mark.parametrize(  # type: ignore[misc]
    ("raw", "expected"),
    [
        ("http://example.com/fit/parse", "http://example.com/fit/parse"),
        ("http://example.com//fit/parse", "http://example.com/fit/parse"),
        ("https://fit.example.com/fit/parse", "https://fit.example.com/fit/parse"),
        ("http://example.com/api//fit/produce", "http://example.com/api/fit/produce"),
    ],
)
def test_normalize_handles_duplicate_fit_segments(raw: str, expected: str) -> None:
    assert client._normalize(raw) == expected
