"""Map Pydantic AR value models to JSON-compatible dicts."""

from pydantic import BaseModel

from bmc.type_defs.json_types import JsonValue


class EntryValuesMapper:
    """Convert typed AR value models to BMC API ``values`` dictionaries."""

    @staticmethod
    def to_values_dict(model: BaseModel) -> dict[str, JsonValue]:
        """Serialize a Pydantic model to AR field names and JSON scalars.

        Parameters
        ----------
        model : BaseModel
            AR values model (field aliases match BMC form names).

        Returns
        -------
        dict[str, JsonValue]
            Flat ``values`` map with ``None`` fields omitted.
        """
        raw = model.model_dump(by_alias=True, exclude_none=True)
        result: dict[str, JsonValue] = {}
        for key, val in raw.items():
            result[str(key)] = coerce_json_value(val)
        return result

    @staticmethod
    def wrap_entry_body(model: BaseModel) -> dict[str, dict[str, JsonValue]]:
        """Wrap serialized values in the BMC POST/PUT body shape.

        Parameters
        ----------
        model : BaseModel
            AR values model to serialize.

        Returns
        -------
        dict[str, dict[str, JsonValue]]
            Body of the form ``{"values": {...}}``.
        """
        return {'values': EntryValuesMapper.to_values_dict(model)}


def coerce_json_value(value: object) -> JsonValue:
    """Normalize a dumped Pydantic value to a JSON-compatible scalar or structure.

    Parameters
    ----------
    value : object
        Raw value from ``model_dump`` (scalar, list, dict, or other).

    Returns
    -------
    JsonValue
        JSON-safe value; unknown types are coerced with ``str()``.
    """
    result: JsonValue
    if value is None or isinstance(value, (str, int, float, bool)):
        result = value  # type: ignore[assignment]
    elif isinstance(value, list):
        result = [coerce_json_value(item) for item in value]
    elif isinstance(value, dict):
        result = {str(dict_key): coerce_json_value(dict_value) for dict_key, dict_value in value.items()}
    else:
        result = str(value)
    return result
