from __future__ import annotations

import logging
import math
from io import BytesIO
from typing import cast

from fastapi import HTTPException
from fit_tool.data_message import DataMessage
from fit_tool.definition_message import DefinitionMessage
from fit_tool.field import Field
from fit_tool.fit_file import FitFile
from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.message_factory import MessageFactory
from fit_tool.record import Record

from .message_registry import resolve as resolve_message
from .models import (
    BuildFitRequest,
    DataField,
    DataRecord,
    DefinitionField,
    DefinitionRecord,
    FitMetadata,
    JSONScalar,
    JSONValue,
    MessageFieldPayload,
    MessagePayload,
    ParseFitResponse,
)

logger = logging.getLogger(__name__)


def parse_fit_bytes(payload: bytes) -> ParseFitResponse:
    try:
        fit_file = FitFile.from_bytes(payload)
    except Exception as exc:  # pragma: no cover - fast failure path
        raise HTTPException(status_code=400, detail=f"Failed to parse FIT file: {exc}") from exc

    metadata = FitMetadata(
        protocol_version=str(fit_file.header.protocol_version),
        profile_version=str(fit_file.header.profile_version),
        records_size=fit_file.header.records_size,
        crc=fit_file.crc,
    )

    records = [_serialize_record(record) for record in fit_file.records]
    return ParseFitResponse(metadata=metadata, records=records)


def build_fit_file(request: BuildFitRequest) -> BytesIO:
    if not request.messages:
        raise HTTPException(
            status_code=400,
            detail="At least one message is required to build a FIT file.",
        )

    builder = FitFileBuilder()
    for message_payload in request.messages:
        message = _message_from_payload(message_payload)
        try:
            builder.add(message)
        except Exception as exc:  # pragma: no cover - builder specific failure
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    fit_file = builder.build()
    return BytesIO(fit_file.to_bytes())


def _serialize_record(record: Record) -> DefinitionRecord | DataRecord:
    if record.is_definition:
        definition = record.message
        if not isinstance(definition, DefinitionMessage):  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail="Malformed FIT definition message.")

        message = MessageFactory.from_definition(definition, developer_fields=[])
        definition_fields = [
            DefinitionField(
                field_id=field.field_id,
                size=field.size,
                base_type=field.base_type.name,
            )
            for field in definition.field_definitions
        ]
        return DefinitionRecord(
            local_id=record.local_id,
            global_id=definition.global_id,
            message=message.name,
            fields=definition_fields,
        )

    data_message = record.message
    fields = [_serialize_data_field(field) for field in data_message.fields if field.is_valid()]
    developer_fields = [
        _serialize_data_field(field) for field in data_message.developer_fields if field.is_valid()
    ]
    combined_fields = fields + developer_fields

    return DataRecord(
        local_id=record.local_id,
        global_id=data_message.global_id,
        message=data_message.name,
        fields=combined_fields,
    )


def _serialize_data_field(field: Field) -> DataField:
    values: list[JSONScalar] = []
    dropped_non_finite = False
    for value in field.get_values():
        if value is None:
            continue
        if isinstance(value, float) and not math.isfinite(value):
            dropped_non_finite = True
            continue
        values.append(cast(JSONScalar, value))

    if not values:
        data_value: JSONValue | None = None
    elif len(values) == 1:
        data_value = values[0]
    else:
        data_value = values

    units = field.units or None

    if dropped_non_finite:
        logger.warning(
            "Omitted non-finite value(s) from field '%s' (id=%s) while serializing FIT data.",
            field.name,
            field.field_id,
        )

    return DataField(
        field_id=field.field_id,
        name=field.name,
        units=units,
        value=data_value,
    )


def _message_from_payload(payload: MessagePayload) -> DataMessage:
    try:
        message_cls = resolve_message(payload.name)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    kwargs = {}
    if payload.local_id is not None:
        kwargs["local_id"] = payload.local_id

    message = message_cls(**kwargs)

    for field in payload.fields:
        _apply_field_payload(message, field)

    return message


def _apply_field_payload(message: DataMessage, field_payload: MessageFieldPayload) -> None:
    field = message.get_field_by_name(field_payload.name)
    if field is None:
        raise HTTPException(
            status_code=400,
            detail=f"Field '{field_payload.name}' is not valid for message '{message.name}'.",
        )

    values = field_payload.resolved_values()
    if not values:
        return

    for index, value in enumerate(values):
        field.set_value(index, value)
