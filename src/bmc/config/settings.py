"""MCP and BMC configuration via Pydantic Settings.

Values are read from the process environment only. No ``.env`` file is loaded at runtime.
"""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class McpServerSettings(BaseSettings):
    """MCP server settings for streamable HTTP transport.

    Loaded from environment variables with prefix ``MCP_``.
    """

    model_config = SettingsConfigDict(
        env_prefix='MCP_',
        extra='ignore',
    )

    host: str = Field(
        default='0.0.0.0',
        description='Bind host for HTTP',
        min_length=1,
        max_length=253,
    )
    port: int = Field(
        default=8000,
        description='Port for HTTP',
        ge=1,
        le=65535,
    )
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = Field(
        default='INFO',
        description='Minimum level for root logger (console and file)',
    )
    log_file: str = Field(
        default='logs/bmc_mcp.log',
        description='Rotating log file path',
        min_length=1,
        max_length=1024,
    )

    @field_validator('log_level', mode='before')
    @classmethod
    def normalize_log_level(cls, value: object) -> str:
        """Normalize log level env value to a supported literal.

        Parameters
        ----------
        value : object
            Raw setting value.

        Returns
        -------
        str
            One of DEBUG, INFO, WARNING, ERROR; defaults to INFO.
        """
        if isinstance(value, str) and value.strip():
            upper = value.strip().upper()
            if upper in ('DEBUG', 'INFO', 'WARNING', 'ERROR'):
                return upper
        return 'INFO'

    @field_validator('port', mode='before')
    @classmethod
    def parse_port(cls, value: object) -> int:
        """Parse port from int or string env value.

        Parameters
        ----------
        value : object
            Raw setting value.

        Returns
        -------
        int
            Port number; defaults to 8000 when unset or invalid.
        """
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip():
            return int(value.strip())
        return 8000


class BmcSettings(BaseSettings):
    """BMC Helix AR API connection and form configuration.

    Loaded from environment variables with prefix ``BMC_``.
    """

    model_config = SettingsConfigDict(
        env_prefix='BMC_',
        extra='ignore',
    )

    base_url: str = Field(
        ...,
        description='BMC REST base URL without trailing slash',
        min_length=1,
    )
    username: str = Field(
        ...,
        description='Service account username (form login)',
        min_length=1,
    )
    password: str = Field(
        ...,
        description='API key / password for service account',
        min_length=1,
    )
    jwt_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    jwt_refresh_margin_seconds: int = Field(default=300, ge=0, le=3600)
    jwt_refresh_interval_seconds: int = Field(
        default=0,
        description='If > 0, fixed refresh loop interval; else TTL - margin',
        ge=0,
    )
    http_timeout_seconds: float = Field(default=30.0, ge=5.0, le=300.0)
    allow_write: bool = Field(default=True)
    max_attachment_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)

    form_incident_create: str = Field(default='HPD:IncidentInterface_Create')
    form_incident_query: str = Field(default='HPD:IncidentInterface')
    form_wo_create: str = Field(default='WOI:WorkOrderInterface_Create')
    form_wo_query: str = Field(default='WOI:WorkOrderInterface')
    form_wo_update: str = Field(default='WOI:WorkOrderInterface')
    form_work_info: str = Field(default='WOI:WorkInfo')

    default_wo_first_name: str = Field(default='Mosaico')
    default_wo_last_name: str = Field(default='WebServices')
    default_wo_company: str = Field(default='ARUS')

    @field_validator('base_url', mode='before')
    @classmethod
    def strip_trailing_slash(cls, value: object) -> str:
        """Strip whitespace and trailing slash from base URL.

        Parameters
        ----------
        value : object
            Raw ``BMC_BASE_URL`` value.

        Returns
        -------
        str
            Normalized base URL without trailing slash.

        Raises
        ------
        ValueError
            When ``value`` is not a string.
        """
        if isinstance(value, str):
            return value.strip().rstrip('/')
        msg = f'BMC_BASE_URL debe ser una URL válida. Valor recibido: {value!r}.'
        raise ValueError(msg)

    @field_validator('http_timeout_seconds', mode='before')
    @classmethod
    def parse_timeout(cls, value: object) -> float:
        """Parse HTTP timeout from numeric or string env value.

        Parameters
        ----------
        value : object
            Raw setting value.

        Returns
        -------
        float
            Timeout in seconds; defaults to 30.0.
        """
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and value.strip():
            return float(value.strip())
        return 30.0

    @field_validator('allow_write', mode='before')
    @classmethod
    def parse_allow_write(cls, value: object) -> bool:
        """Parse allow-write flag from bool or string env value.

        Parameters
        ----------
        value : object
            Raw setting value.

        Returns
        -------
        bool
            Whether mutating MCP tools are allowed.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ('1', 'true', 'yes', 'on')
        return True
