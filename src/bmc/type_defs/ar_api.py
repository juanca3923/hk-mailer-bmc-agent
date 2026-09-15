"""Parsed BMC AR REST API response models."""

from pydantic import BaseModel, Field

from bmc.type_defs.json_types import JsonValue

# Flat JSON scalars for Pydantic (no recursive JsonValue in models).
ArScalarValue = str | int | float | bool | None


class BmcEntryValues(BaseModel):
    """Single entry ``values`` map from an AR list or create response."""

    data: dict[str, ArScalarValue] = Field(default_factory=dict[str, ArScalarValue])

    def get_str(self, key: str, default: str = "") -> str:
        """Return a string field or *default* if missing or not a string.

        Parameters
        ----------
        key : str
            AR field name in ``data``.
        default : str, optional
            Value when the field is missing or not a string, by default ``''``.

        Returns
        -------
        str
            String representation of the field value.
        """
        # pylint: disable=no-member
        raw = self.data.get(key)
        # pylint: enable=no-member
        if isinstance(raw, str):
            return raw
        if raw is not None:
            return str(raw)
        return default


class BmcEntry(BaseModel):
    """One element of ``entries`` in a BMC list/search response."""

    values: BmcEntryValues = Field(default_factory=BmcEntryValues)


class BmcEntryListResponse(BaseModel):
    """GET list/search response shape from the AR API."""

    entries: list[BmcEntry] = Field(default_factory=list)

    def first_values(self) -> BmcEntryValues | None:
        """Return the ``values`` map of the first entry, if any.

        Returns
        -------
        BmcEntryValues | None
            First entry values, or ``None`` when ``entries`` is empty.
        """
        if not self.entries:
            return None
        return self.entries[0].values


class BmcCreateEntryResponse(BaseModel):
    """POST create response with values and optional Location-derived ids."""

    values: BmcEntryValues = Field(default_factory=BmcEntryValues)
    location: str = Field(default="")


def _coerce_scalar(val: JsonValue) -> ArScalarValue:
    """Coerce a raw JSON value to an AR scalar, stringifying anything else.

    Parameters
    ----------
    val : JsonValue
        Raw value from a BMC ``values`` map.

    Returns
    -------
    ArScalarValue
        ``val`` unchanged when it is already a scalar (or ``None``); otherwise ``str(val)``.
    """
    if isinstance(val, (str, int, float, bool)) or val is None:
        return val
    return str(val)


def _parse_values_dict(raw_values: JsonValue) -> dict[str, ArScalarValue]:
    """Parse a raw ``values`` JSON object into a flat scalar dict.

    Parameters
    ----------
    raw_values : JsonValue
        Raw ``values`` field from an AR entry or create response.

    Returns
    -------
    dict[str, ArScalarValue]
        Empty when ``raw_values`` is not a JSON object.
    """
    if not isinstance(raw_values, dict):
        return {}
    return {str(key): _coerce_scalar(val) for key, val in raw_values.items()}


def _parse_entry(item: JsonValue) -> BmcEntry | None:
    """Parse one raw ``entries`` element into a ``BmcEntry``.

    Parameters
    ----------
    item : JsonValue
        Raw entry from the ``entries`` list.

    Returns
    -------
    BmcEntry | None
        Parsed entry, or ``None`` when ``item`` is not a JSON object.
    """
    if not isinstance(item, dict):
        return None
    return BmcEntry(values=BmcEntryValues(data=_parse_values_dict(item.get("values"))))


def parse_entry_list(payload: JsonValue) -> BmcEntryListResponse:
    """Parse a BMC list/search JSON body into ``BmcEntryListResponse``.

    Parameters
    ----------
    payload : JsonValue
        Raw JSON from an AR GET list endpoint.

    Returns
    -------
    BmcEntryListResponse
        Parsed entries; empty when the payload shape is invalid.
    """
    if not isinstance(payload, dict):
        return BmcEntryListResponse()
    raw_entries = payload.get("entries")
    if not isinstance(raw_entries, list):
        return BmcEntryListResponse()
    entries = [entry for entry in (_parse_entry(item) for item in raw_entries) if entry is not None]
    return BmcEntryListResponse(entries=entries)


def parse_create_response(payload: JsonValue, location: str = "") -> BmcCreateEntryResponse:
    """Parse a BMC create JSON body into ``BmcCreateEntryResponse``.

    Parameters
    ----------
    payload : JsonValue
        Raw JSON from an AR POST create endpoint.
    location : str, optional
        ``Location`` response header value, by default ``''``.

    Returns
    -------
    BmcCreateEntryResponse
        Parsed values map and location string.
    """
    raw_values = payload.get("values") if isinstance(payload, dict) else None
    return BmcCreateEntryResponse(
        values=BmcEntryValues(data=_parse_values_dict(raw_values)),
        location=location,
    )
