from typing import cast

from pydantic import BaseModel

JSONScalar = str | int | float | bool | None
JSONDict = dict[str, "JSONValue"]
JSONList = list["JSONValue"]
JSONValue = JSONScalar | JSONDict | JSONList

ENGINE_FIELDS: set[str] = {
    "question_types",
    "constraints",
}


def _remove_engine_fields(data: JSONValue) -> JSONValue:
    if isinstance(data, dict):
        result: JSONDict = {}
        for key, value in data.items():
            if key not in ENGINE_FIELDS:
                result[key] = _remove_engine_fields(value)
        return result

    if isinstance(data, list):
        return [_remove_engine_fields(item) for item in data]

    return data


def model_dump_minimal(obj: BaseModel) -> JSONValue:
    data = cast(JSONDict, obj.model_dump())
    return _remove_engine_fields(data)


__all__ = ["model_dump_minimal"]
