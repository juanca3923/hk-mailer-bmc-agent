"""JSON-compatible value types for BMC API payloads (no Any)."""

from typing import TypeAlias

JsonValue: TypeAlias = str | int | float | bool | None | list['JsonValue'] | dict[str, 'JsonValue']
