"""Modelos de la base de datos."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Double, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from database.constants import EVENT_TYPE_DB_LEN, SHORT_STRING_DB_LEN
from type_defs.enums.domain_literals import MESSAGE_TYPE_NORMAL
from type_defs.models.common.json_types import JsonDict

NOW_SQL = text("now()")
DELETE_CASCADE_SQL = "all, delete-orphan"


class Base(DeclarativeBase):
    """Base model for all models."""


class Chat(Base):
    """Sesión de conversación que agrupa múltiples turnos usuario/asistente."""

    __tablename__ = "chats"

    id: Mapped[UUID] = mapped_column(PG_UUID[UUID](as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=NOW_SQL)
    # Denormalizado para ordenar/listar chats sin JOIN costoso
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=NOW_SQL)

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="chat",
        cascade=DELETE_CASCADE_SQL,
        lazy="selectin",
        order_by="ChatMessage.ts",
    )
    runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="chat",
        cascade=DELETE_CASCADE_SQL,
        lazy="noload",
    )


class ChatMessage(Base):
    """Mensaje individual dentro de un chat (usuario o asistente)."""

    __tablename__ = "chat_messages"

    id: Mapped[UUID] = mapped_column(PG_UUID[UUID](as_uuid=True), primary_key=True, default=uuid4)
    chat_id: Mapped[UUID] = mapped_column(
        PG_UUID[UUID](as_uuid=True),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # "user" | "assistant"
    role: Mapped[str] = mapped_column(String(SHORT_STRING_DB_LEN), nullable=False)
    # "normal" | "error" | "cancelled"
    message_type: Mapped[str] = mapped_column(
        String(SHORT_STRING_DB_LEN), nullable=False, server_default=MESSAGE_TYPE_NORMAL
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    # Solo presente en mensajes role=assistant; traza al run que generó la respuesta
    agent_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID[UUID](as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    chat: Mapped[Chat] = relationship(back_populates="messages", lazy="joined")


class AgentRun(Base):
    """Ejecución individual del agente con métricas y trazabilidad."""

    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(PG_UUID[UUID](as_uuid=True), primary_key=True, default=uuid4)
    # Nullable para retrocompatibilidad con runs anteriores sin chat
    chat_id: Mapped[UUID | None] = mapped_column(
        PG_UUID[UUID](as_uuid=True),
        ForeignKey("chats.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=NOW_SQL)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_time: Mapped[float | None] = mapped_column(Double, nullable=True)

    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    final_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(SHORT_STRING_DB_LEN), nullable=False, index=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    total_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    chat: Mapped[Chat | None] = relationship(back_populates="runs", lazy="noload")
    events: Mapped[list["AgentEvent"]] = relationship(
        back_populates="agent_run",
        cascade=DELETE_CASCADE_SQL,
        lazy="selectin",
    )


class AgentEvent(Base):
    """Evento de bajo nivel de una ejecución (llm_start, tool_start, llm_end, etc.)."""

    __tablename__ = "agent_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_run_id: Mapped[UUID] = mapped_column(
        PG_UUID[UUID](as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(EVENT_TYPE_DB_LEN), nullable=False, index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=NOW_SQL)
    payload: Mapped[JsonDict] = mapped_column(JSONB, nullable=False)

    agent_run: Mapped[AgentRun] = relationship(back_populates="events", lazy="joined")


class AgentMemoryFact(Base):
    """Hecho persistido en el store cross-thread de LangGraph (AgentPostgresStore).

    Cada fila representa un dato que el agente puede leer y escribir entre conversaciones
    distintas. La clave lógica es (namespace, key); el valor es un dict JSONB libre.
    """

    __tablename__ = "agent_memory_facts"
    __table_args__ = (UniqueConstraint("namespace", "key", name="uq_agent_memory_facts_ns_key"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    namespace: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[JsonDict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=NOW_SQL)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=NOW_SQL)
