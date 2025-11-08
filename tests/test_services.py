from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from fitfile_customgpt_action import services
from fitfile_customgpt_action.models import BuildFitRequest, MessageFieldPayload, MessagePayload

from .pytest_types import parametrize


class DummyField:
    def __init__(self, field_id: int, name: str, values: list[Any]) -> None:
        self.field_id: int = field_id
        self.name: str = name
        self._values = list(values)
        self.units: str = "units"
        self.calls: list[tuple[int, Any]] = []

    def get_values(self) -> list[Any]:
        return list(self._values)

    def is_valid(self) -> bool:
        return True

    def set_value(self, index: int, value: Any) -> None:
        self.calls.append((index, value))


class DummyMessage:
    name = "dummy-message"

    def __init__(self, local_id: int = 0) -> None:
        self.local_id = local_id
        self.fields: list[DummyField] = [DummyField(1, "alpha", []), DummyField(2, "beta", [])]
        self.developer_fields: list[DummyField] = []

    def get_field_by_name(self, name: str) -> DummyField | None:
        return next((field for field in self.fields if field.name == name), None)


@parametrize(
    ("field_values", "expected_value"),
    [([42], 42), ([1, 2], [1, 2])],
)
def test_parse_fit_bytes_success(
    monkeypatch: pytest.MonkeyPatch, field_values: list[int], expected_value: int | list[int]
) -> None:
    class DummyProtocol:
        def __str__(self) -> str:
            return "2.0"

    class DummyProfile:
        def __str__(self) -> str:
            return "21.60"

    class DummyBaseType:
        def __init__(self, name: str) -> None:
            self.name: str = name

    class DummyDefinitionField:
        def __init__(self) -> None:
            self.field_id: int = 7
            self.size: int = 4
            self.base_type: DummyBaseType = DummyBaseType("UINT32")

    class DummyDefinitionMessage:
        def __init__(self) -> None:
            self.global_id: int = 200
            self.field_definitions: list[DummyDefinitionField] = [DummyDefinitionField()]

    class DummyFactory:
        @staticmethod
        def from_definition(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(name="definition-message")

    class DummyDataField(DummyField):
        def __init__(self, field_id: int, name: str, values: list[Any], units: str) -> None:
            super().__init__(field_id, name, values)
            self.units = units

    class DummyDataMessage:
        def __init__(self, values: list[int]) -> None:
            self.global_id: int = 300
            self.name = "data"
            self.fields: list[DummyDataField] = [DummyDataField(10, "speed", values, "m/s")]
            self.developer_fields: list[DummyDataField] = [
                DummyDataField(11, "dev-field", [99], "")
            ]

    definition_message = DummyDefinitionMessage()
    definition_record = SimpleNamespace(is_definition=True, local_id=0, message=definition_message)
    data_record = SimpleNamespace(
        is_definition=False,
        local_id=1,
        message=DummyDataMessage(field_values),
    )

    header = SimpleNamespace(
        protocol_version=DummyProtocol(),
        profile_version=DummyProfile(),
        records_size=128,
    )
    fake_fit_file = SimpleNamespace(
        header=header,
        records=[definition_record, data_record],
        crc=0xABCD,
    )

    class DummyFitFileAPI:
        @staticmethod
        def from_bytes(_payload: bytes) -> SimpleNamespace:
            return fake_fit_file

    monkeypatch.setattr(services, "FitFile", DummyFitFileAPI)
    monkeypatch.setattr(services, "DefinitionMessage", DummyDefinitionMessage)
    monkeypatch.setattr(services, "MessageFactory", DummyFactory)

    response = services.parse_fit_bytes(b"payload")
    assert response.metadata.protocol_version == "2.0"
    assert response.metadata.profile_version == "21.60"
    assert response.metadata.records_size == 128
    assert response.metadata.crc == 0xABCD

    definition = response.records[0]
    assert definition.kind == "definition"
    assert definition.fields[0].base_type == "UINT32"

    data = response.records[1]
    assert data.kind == "data"
    assert data.fields[0].value == expected_value
    assert data.fields[0].units == "m/s"
    assert data.fields[1].value == 99


def test_parse_fit_bytes_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyFitFileAPI:
        @staticmethod
        def from_bytes(_payload: bytes) -> SimpleNamespace:
            raise ValueError("boom")

    monkeypatch.setattr(services, "FitFile", DummyFitFileAPI)

    with pytest.raises(Exception) as exc:
        services.parse_fit_bytes(b"payload")
    assert "Failed to parse FIT file" in str(exc.value)


@parametrize(
    ("field_payload_groups", "expected_calls"),
    [
        (
            [[{"name": "alpha", "value": 5}]],
            [{"alpha": [(0, 5)], "beta": []}],
        ),
        (
            [
                [
                    {"name": "alpha", "values": [3, 4]},
                    {"name": "beta", "value": 9},
                ],
                [{"name": "alpha", "value": 1}],
            ],
            [
                {"alpha": [(0, 3), (1, 4)], "beta": [(0, 9)]},
                {"alpha": [(0, 1)], "beta": []},
            ],
        ),
    ],
)
def test_build_fit_file_success(
    monkeypatch: pytest.MonkeyPatch,
    field_payload_groups: list[list[dict[str, Any]]],
    expected_calls: list[dict[str, list[tuple[int, Any]]]],
) -> None:
    created: dict[str, DummyBuilder] = {}

    class DummyBuiltFitFile:
        @staticmethod
        def to_bytes() -> bytes:
            return b"FIT"

    class DummyBuilder:
        def __init__(self) -> None:
            self.added: list[DummyMessage] = []

        def add(self, message: DummyMessage) -> None:
            self.added.append(message)

        def build(self) -> DummyBuiltFitFile:
            return DummyBuiltFitFile()

    def builder_factory() -> DummyBuilder:
        builder = DummyBuilder()
        created["instance"] = builder
        return builder

    monkeypatch.setattr(services, "FitFileBuilder", builder_factory)
    monkeypatch.setattr(services, "resolve_message", lambda _name: DummyMessage)

    request = BuildFitRequest(
        messages=[
            MessagePayload(
                name="dummy-message",
                fields=[MessageFieldPayload(**field_dict) for field_dict in message_fields],
            )
            for message_fields in field_payload_groups
        ]
    )

    result_stream = services.build_fit_file(request)
    assert result_stream.read() == b"FIT"

    builder = created["instance"]
    assert len(builder.added) == len(field_payload_groups)

    for message, expected in zip(builder.added, expected_calls, strict=True):
        for field in message.fields:
            assert field.calls == expected.get(field.name, [])


def test_build_fit_file_without_messages() -> None:
    with pytest.raises(Exception) as exc:
        services.build_fit_file(BuildFitRequest())
    assert "At least one message" in str(exc.value)


def test_build_fit_file_builder_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingBuilder:
        def add(self, _message: DummyMessage) -> None:
            raise ValueError("builder error")

        def build(self) -> None:
            raise AssertionError("should not build")

    def failing_builder_factory() -> FailingBuilder:
        return FailingBuilder()

    monkeypatch.setattr(services, "FitFileBuilder", failing_builder_factory)
    monkeypatch.setattr(services, "resolve_message", lambda _name: DummyMessage)

    request = BuildFitRequest(
        messages=[
            MessagePayload(
                name="dummy-message",
                fields=[MessageFieldPayload(name="alpha", value=1)],
            )
        ]
    )

    with pytest.raises(Exception) as exc:
        services.build_fit_file(request)
    assert "builder error" in str(exc.value)


def test_message_from_payload_unknown_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolver(_name: str) -> type[DummyMessage]:
        raise KeyError("unknown")

    monkeypatch.setattr(services, "resolve_message", resolver)

    payload = MessagePayload(name="missing", fields=[])
    with pytest.raises(Exception) as exc:
        services._message_from_payload(payload)
    assert "unknown" in str(exc.value)


def test_apply_field_payload_rejects_unknown_field() -> None:
    class MessageWithoutFields:
        name = "dummy-message"

        @staticmethod
        def get_field_by_name(_name: str) -> None:
            return None

    with pytest.raises(Exception) as exc:
        services._apply_field_payload(
            MessageWithoutFields(),
            MessageFieldPayload(name="alpha", value=1),
        )
    assert "Field 'alpha'" in str(exc.value)
