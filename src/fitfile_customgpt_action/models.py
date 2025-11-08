from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list[JSONScalar]


class FitMetadata(BaseModel):
    protocol_version: str
    profile_version: str
    records_size: int
    crc: int | None = None


class DefinitionField(BaseModel):
    field_id: int
    size: int
    base_type: str


class DefinitionRecord(BaseModel):
    kind: Literal["definition"] = "definition"
    local_id: int
    global_id: int
    message: str
    fields: list[DefinitionField]


class DataField(BaseModel):
    field_id: int
    name: str
    units: str | None = None
    value: JSONValue | None = None


class DataRecord(BaseModel):
    kind: Literal["data"] = "data"
    local_id: int
    global_id: int
    message: str
    fields: list[DataField]


FitRecord = Annotated[DefinitionRecord | DataRecord, Field(discriminator="kind")]


class ParseFitResponse(BaseModel):
    metadata: FitMetadata
    records: list[FitRecord]


class MessageFieldPayload(BaseModel):
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
    name: str
    local_id: int | None = None
    fields: list[MessageFieldPayload] = Field(default_factory=list)


class BuildFitRequest(BaseModel):
    messages: list[MessagePayload] = Field(default_factory=list)
