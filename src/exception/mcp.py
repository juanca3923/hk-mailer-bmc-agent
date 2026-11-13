"""MCP-related exceptions with actionable error messages."""


class MCPClientError(Exception):
    """Client or API error surfaced to MCP tools.

    Attributes
    ----------
    message : str
        User-facing error text.
    status_code : int | None
        HTTP status when applicable.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class MCPValidationError(Exception):
    """Raised when input validation fails (e.g. Pydantic).

    Attributes
    ----------
    message : str
        Summary validation error message.
    details : list[str]
        Optional field-level detail strings.
    """

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        self.message = message
        self.details = details or []
        super().__init__(self.message)


class MCPLoginError(MCPClientError):
    """Raised when BMC JWT login fails at startup or refresh."""
