"""Configuración de AgentForge."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal, Self

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from constants.config import AGENT_SLUG_RE

logger = logging.getLogger(__name__)


def system_prompt_path() -> Path:
    """Ruta por defecto al prompt principal en la raíz del repo (`system.promt.md`)."""
    return Settings.repo_root() / "system.promt.md"


def skills_dir() -> Path:
    """Directorio fijo de guías/skills Markdown en la raíz del repo (`skills/`)."""
    return Settings.repo_root() / "skills"


class Settings(BaseSettings):
    """Configuración de AgentForge."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    ollama_base_url: str = Field(default="", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="", alias="OLLAMA_MODEL")

    llm_provider: Literal["ollama", "openai", "anthropic", "huggingface"] = Field(
        alias="LLM_PROVIDER",
    )
    # Temperatura de muestreo compartida por los 4 proveedores. Antes era 0.6 fijo en
    # `build_llm`; se expone como opcional con ese mismo valor por defecto.
    llm_temperature: float = Field(default=0.6, alias="LLM_TEMPERATURE")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="", alias="OPENAI_MODEL")
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="", alias="ANTHROPIC_MODEL")
    huggingface_api_key: str = Field(default="", alias="HUGGINGFACE_API_KEY")
    huggingface_model: str = Field(default="", alias="HUGGINGFACE_MODEL")
    # Proveedor de inferencia detrás del router de HF Inference Providers (p.ej. "together",
    # "novita", "cerebras"). Vacío -> "auto" (HF elige el primero disponible para el modelo).
    huggingface_provider: str = Field(default="", alias="HUGGINGFACE_PROVIDER")
    # Nombre de la organización de HF a la que facturar el consumo de inferencia
    # (equivalente a InferenceClient(bill_to=...)). Vacío -> se factura a la cuenta del token.
    huggingface_bill_to: str = Field(default="", alias="HUGGINGFACE_BILL_TO")
    # Límite de tokens de salida para el endpoint HF. Antes era 2048 fijo en
    # `get_huggingface_llm`; se expone como opcional con ese mismo valor por defecto.
    huggingface_max_new_tokens: int = Field(default=2048, alias="HUGGINGFACE_MAX_NEW_TOKENS")
    # SOLO para redes corporativas con inspección TLS cuyo CA raíz usa una clave RSA débil
    # (<2048 bits) o firma SHA-1: relaja el nivel de seguridad de OpenSSL (SECLEVEL=1) para
    # el cliente HTTP de huggingface_hub. La verificación del certificado sigue activa (no
    # equivale a verify=False); solo se acepta un algoritmo/tamaño de clave ya obsoleto.
    # Requiere además `SSL_CERT_FILE` apuntando a un bundle que incluya ese CA corporativo.
    # NUNCA activar en producción: el arreglo correcto es que el CA se reemita con clave >= 2048.
    huggingface_allow_legacy_tls: bool = Field(default=False, alias="HUGGINGFACE_ALLOW_LEGACY_TLS")

    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="", alias="LANGFUSE_HOST")
    langfuse_prompt_name: str = Field(default="", alias="LANGFUSE_PROMPT_NAME")
    langfuse_prompt_label: str = Field(default="latest", alias="LANGFUSE_PROMPT_LABEL")
    langfuse_ssl_verify: bool = Field(default=True, alias="LANGFUSE_SSL_VERIFY")

    # Lista separada por comas. Ej: "http://localhost:8001/mcp,http://localhost:9000/mcp"
    mcp_urls: str = Field(default="", alias="MCP_URLS")

    stream: bool = Field(default=False, alias="STREAM")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    http_host: str = Field(default="0.0.0.0", alias="HTTP_HOST")
    http_port: int = Field(alias="HTTP_PORT")

    # CORS: lista separada por comas o "*" para permitir cualquier origen.
    # Si ``cors_allow_credentials`` es True, no uses "*" (los navegadores lo rechazan).
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")

    # Si es True (por defecto): se permiten turnos concurrentes en POST /chat,
    # POST /chat/stream y A2A (cada chat ya está aislado por su propio UUID/thread_id en
    # el checkpointer, así que correrlos en paralelo no mezcla estado entre chats). Si es
    # False: un run por turno — un turno nuevo se rechaza con 409 mientras haya uno en
    # curso.
    http_allow_concurrent_turns: bool = Field(default=True, alias="HTTP_ALLOW_CONCURRENT_TURNS")

    # Identificador de instancia (BD, logs, A2A por defecto). Patrón: ^[a-z][a-z0-9_]*$
    agent_slug: str = Field(default="agent_forge", alias="AGENT_SLUG")
    # Nombre visible (Agent Card). Vacío → título a partir del slug.
    agent_display_name: str = Field(default="", alias="AGENT_DISPLAY_NAME")
    # Descripción corta de la Agent Card A2A (cada instancia / despliegue).
    agent_card_description: str = Field(default="", alias="AGENT_CARD_DESCRIPTION")

    # Texto completo del system prompt. Si no está vacío, tiene prioridad sobre archivo.
    system_prompt_env: str = Field(default="", alias="SYSTEM_PROMPT")
    # Ruta al archivo de prompt principal (absoluta o relativa a la raíz del repo).
    system_prompt_path_env: str = Field(default="", alias="SYSTEM_PROMPT_PATH")

    # Vacío → se usa ``agent_slug`` como ``assistant_id`` A2A local.
    a2a_assistant_id: str = Field(default="", alias="A2A_ASSISTANT_ID")
    a2a_protocol_version: str = Field(default="0.2.6", alias="A2A_PROTOCOL_VERSION")
    # Peers A2A (outbound): comas. Cada entrada DEBE ser ``url_base|assistant_id`` del peer remoto.
    a2a_peer_urls: str = Field(default="", alias="A2A_PEER_URLS")

    # Postgres (auditoría/logs de ejecuciones del agente)
    database_url: str = Field(alias="DATABASE_URL")
    db_echo: bool = Field(default=False, alias="DB_ECHO")

    # Zona horaria IANA usada por la tool `get_current_date` (nombre de ``zoneinfo``,
    # ej. "America/Bogota"). Por defecto Colombia; independiente del TZ del SO del contenedor.
    agent_timezone: str = Field(default="America/Bogota", alias="AGENT_TIMEZONE")

    @field_validator("llm_provider", mode="before")
    @classmethod
    def normalize_llm_provider(cls, value: object) -> str:
        raw = (str(value).strip().lower() if value is not None else "") or "ollama"
        if raw not in ("ollama", "openai", "anthropic", "huggingface"):
            msg = "LLM_PROVIDER debe ser uno de: ollama, openai, anthropic, huggingface"
            raise ValueError(msg)
        return raw

    @field_validator("agent_slug")
    @classmethod
    def validate_agent_slug(cls, value: str) -> str:
        slug = (value or "").strip()
        if not AGENT_SLUG_RE.match(slug):
            msg = (
                "AGENT_SLUG debe coincidir con ^[a-z][a-z0-9_]*$ "
                "(minúscula inicial, luego letras minúsculas, dígitos o _)"
            )
            raise ValueError(msg)
        return slug

    @model_validator(mode="after")
    def validate_provider_keys_and_langfuse(self) -> Self:
        self._validate_provider_required_keys()
        self._validate_langfuse_prompt_required_keys()
        return self

    def _required_fields_for_provider(self) -> list[tuple[str, str]]:
        """Campos obligatorios (valor, nombre de variable de entorno) para ``llm_provider``.

        Returns
        -------
        list[tuple[str, str]]
            Pares ``(valor, ENV_VAR)`` en el orden en que deben validarse; vacío si el
            proveedor activo no tiene campos adicionales que validar aquí.
        """
        by_provider: dict[str, list[tuple[str, str]]] = {
            "ollama": [(self.ollama_model, "OLLAMA_MODEL")],
            "openai": [(self.openai_api_key, "OPENAI_API_KEY")],
            "anthropic": [(self.anthropic_api_key, "ANTHROPIC_API_KEY")],
            "huggingface": [
                (self.huggingface_api_key, "HUGGINGFACE_API_KEY"),
                (self.huggingface_model, "HUGGINGFACE_MODEL"),
            ],
        }
        return by_provider.get(self.llm_provider, [])

    def _validate_provider_required_keys(self) -> None:
        """Lanza ``ValueError`` si falta algún campo obligatorio del ``llm_provider`` activo."""
        for value, env_name in self._required_fields_for_provider():
            if not (value or "").strip():
                msg = f"{env_name} es obligatorio cuando LLM_PROVIDER={self.llm_provider}"
                raise ValueError(msg)

    @staticmethod
    def repo_root() -> Path:
        """Raíz del repositorio (directorio que contiene ``system.promt.md`` y ``skills/``)."""
        return Path(__file__).resolve().parents[2]

    @classmethod
    def load(cls) -> "Settings":
        """Carga la configuración desde el archivo .env."""
        load_dotenv(override=False)
        return cls()

    @property
    def effective_a2a_assistant_id(self) -> str:
        """``A2A_ASSISTANT_ID`` explícito, o ``agent_slug`` si no se definió."""
        explicit = (self.a2a_assistant_id or "").strip()
        return explicit if explicit else self.agent_slug

    @property
    def effective_agent_display_name(self) -> str:
        """Nombre para Agent Card; por defecto un título legible derivado del slug."""
        name = (self.agent_display_name or "").strip()
        if name:
            return name
        return str(self.agent_slug).replace("_", " ").title()

    @property
    def effective_agent_card_description(self) -> str:
        """Texto ``description`` de la Agent Card; por defecto mensaje genérico + slug."""
        text = (self.agent_card_description or "").strip()
        if text:
            return text
        return (
            "Agente que registra y consulta incidentes y órdenes de trabajo en BMC Helix ARUS. "
            "Para crear un ticket requiere el correo real de la persona solicitante (nunca inventado) y la "
            "descripción del caso; para consultar un ticket requiere su número (INC... o WO...) o el correo del "
            "solicitante. Los casos se registran y quedan abiertos. "
            f"Instancia: {self.agent_slug}."
        )

    @property
    def langfuse_tracing_ready(self) -> bool:
        """True si hay credenciales suficientes para el callback de trazas en Langfuse."""
        return bool(
            (self.langfuse_public_key or "").strip()
            and (self.langfuse_secret_key or "").strip()
            and (self.langfuse_host or "").strip()
        )

    @property
    def asyncpg_url(self) -> str:
        """URL de conexión en formato nativo de asyncpg (sin prefijo +asyncpg de SQLAlchemy).

        asyncpg.create_pool() espera 'postgresql://...' en lugar de 'postgresql+asyncpg://...'.
        """
        return str(self.database_url).replace("postgresql+asyncpg://", "postgresql://", 1)

    @staticmethod
    def get_value_or_empty(value: str | None) -> str:
        """Obtiene el valor de una cadena y lo convierte a cadena vacía si es None."""
        return (value or "").strip()

    def _validate_langfuse_prompt_required_keys(self) -> None:
        name = self.get_value_or_empty(self.langfuse_prompt_name)
        if name:
            missing: list[str] = []
            if not self.get_value_or_empty(self.langfuse_public_key):
                missing.append("LANGFUSE_PUBLIC_KEY")
            if not self.get_value_or_empty(self.langfuse_secret_key):
                missing.append("LANGFUSE_SECRET_KEY")
            if not self.get_value_or_empty(self.langfuse_host):
                missing.append("LANGFUSE_HOST")
            if not self.get_value_or_empty(self.langfuse_prompt_label):
                missing.append("LANGFUSE_PROMPT_LABEL")
            if missing:
                msg = "Si LANGFUSE_PROMPT_NAME está definido, deben configurarse: " + ", ".join(missing)
                raise ValueError(msg)

    def resolved_system_prompt_file(self) -> Path:
        """Archivo principal del system prompt cuando no se usa ``SYSTEM_PROMPT``."""
        raw = (self.system_prompt_path_env or "").strip()
        if raw:
            path = Path(raw)
            if not path.is_absolute():
                path = self.repo_root() / path
            return path
        return self.repo_root() / "system.promt.md"

    def normalized_cors_origins(self) -> list[str]:
        """Orígenes permitidos para CORSMiddleware (coma‑separados o ``*``)."""
        raw = (self.cors_origins or "").strip()
        if not raw or raw == "*":
            return ["*"]
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        return parts if parts else ["*"]

    def normalized_mcp_urls(self) -> list[str]:
        """Normaliza las URLs MCP separadas por comas."""
        urls = [mcp.strip() for mcp in str(self.mcp_urls).split(",") if mcp.strip()]
        return list(dict.fromkeys(urls))

    def normalized_a2a_peer_configs(self) -> list[tuple[str, str]]:
        """Pares (base_url, assistant_id) para cada peer A2A remoto.

        Cada segmento (coma-separado) en ``a2a_peer_urls`` debe ser exactamente
        ``url_base|assistant_id`` con ambas partes no vacías tras ``strip``.
        Cualquier otro formato se omite (no queda disponible para consumo) y se registra WARNING.
        """
        seen: dict[tuple[str, str], None] = {}
        out: list[tuple[str, str]] = []
        for position, raw in enumerate(str(self.a2a_peer_urls).split(","), start=1):
            segment = raw.strip()
            if not segment:
                continue
            if "|" not in segment:
                logger.warning(
                    "A2A_PEER_URLS: entrada #%d omitida (se requiere formato 'url|agent_id')",
                    position,
                )
                continue
            base_part, aid_part = segment.split("|", 1)
            base_url = base_part.strip().rstrip("/")
            peer_aid = aid_part.strip()
            if not base_url or not peer_aid:
                logger.warning(
                    "A2A_PEER_URLS: entrada #%d omitida (url y agent_id no vacíos)",
                    position,
                )
                continue
            key = (base_url, peer_aid)
            if key not in seen:
                seen[key] = None
                out.append(key)
        return out
