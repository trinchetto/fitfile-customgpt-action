"""Pydantic schemas that describe FIT parse responses and builder requests."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

# Scalars that safely round-trip through JSON; used by fields and payloads.
JSONScalar = str | int | float | bool | None
# Field values can be a single scalar or a list of scalars.
JSONValue = JSONScalar | list[JSONScalar]


class FitMetadata(BaseModel):
    """Parsed FIT file header metadata."""

    protocol_version: str
    profile_version: str
    records_size: int
    crc: int | None = None


class DefinitionField(BaseModel):
    """Field definition discovered in a FIT definition record."""

    field_id: int
    size: int
    base_type: str


class DefinitionRecord(BaseModel):
    """Definition record emitted when parsing FIT files."""

    kind: Literal["definition"] = "definition"
    local_id: int
    global_id: int
    message: str
    fields: list[DefinitionField]


class DataField(BaseModel):
    """Concrete field value extracted from a FIT data record."""

    field_id: int
    name: str
    units: str | None = None
    value: JSONValue | None = None


class DataRecord(BaseModel):
    """Data record emitted when parsing FIT files."""

    kind: Literal["data"] = "data"
    local_id: int
    global_id: int
    message: str
    fields: list[DataField]


FitRecord = Annotated[DefinitionRecord | DataRecord, Field(discriminator="kind")]


class ParseFitResponse(BaseModel):
    """Full response model for the `/fit/parse` endpoint."""

    metadata: FitMetadata
    records: list[FitRecord]


class MessageFieldPayload(BaseModel):
    """Flexible representation for supplying single or repeated field values."""

    name: str
    value: JSONValue | None = None
    values: list[JSONScalar] | None = None

    @field_validator("value", mode="before")
    @classmethod
    def _flatten_value(cls, incoming: object) -> object:
        if isinstance(incoming, list):
            # If a list arrives via "value", treat it as explicit values.
            return [item for item in incoming]
        return incoming

    def resolved_values(self) -> list[JSONScalar]:
        if self.values is not None:
            return list(self.values)

        if self.value is None:
            return []

        if isinstance(self.value, list):
            return list(self.value)

        return [self.value]


class MessagePayload(BaseModel):
    """Name + optional local_id + field payloads for building FIT data messages."""

    name: str
    local_id: int | None = None
    fields: list[MessageFieldPayload] = Field(default_factory=list)


class BuildFitRequest(BaseModel):
    """Request body accepted by the `/fit/produce` endpoint."""

    messages: list[MessagePayload] = Field(default_factory=list)
