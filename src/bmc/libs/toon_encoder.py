"""TOON encoding for token-efficient tool responses."""

from typing import cast

from pydantic import BaseModel
from toon import ToonEncoder

from bmc.type_defs.json_types import JsonValue

encoder = ToonEncoder()


class ToonResponseEncoder:
    """Encode structured data as TOON strings for MCP tool responses."""

    @staticmethod
    def encode(data: dict[str, JsonValue] | list[JsonValue]) -> str:
        """Encode a dict or list to TOON format.

        Parameters
        ----------
        data : dict[str, JsonValue] | list[JsonValue]
            JSON-compatible structure to encode.

        Returns
        -------
        str
            TOON-formatted string for ``BaseOutput.message``.
        """
        return cast("str", encoder.encode(data))

    @staticmethod
    def encode_model(model: BaseModel) -> str:
        """Encode a Pydantic model as TOON via a JSON-compatible dict.

        Parameters
        ----------
        model : BaseModel
            Model to serialize with ``model_dump(mode='json')``.

        Returns
        -------
        str
            TOON-formatted string for ``BaseOutput.message``.
        """
        dumped = model.model_dump(mode='json')
        if isinstance(dumped, dict):
            return cast("str", encoder.encode(dumped))
        return cast("str", encoder.encode({'data': dumped}))
