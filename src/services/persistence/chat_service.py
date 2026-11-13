"""Servicio para gestión de chats y mensajes de conversación."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from uuid import UUID, uuid4

from sqlalchemy import select, update

from config import get_logger
from constants.agent import SEARCH_PREVIEW_MAX_LEN
from database.engine import get_session
from database.models import Chat, ChatMessage
from type_defs.enums.domain_literals import (
    MESSAGE_TYPE_NORMAL,
    ChatRole,
    MessageType,
)
from type_defs.models.agent.search_results import ChatSearchResult


class ChatService:
    """Gestiona chats y sus mensajes: creación, persistencia y consulta."""

    def __init__(self) -> None:
        self.logger = get_logger()

    # ------------------------------------------------------------------
    # Gestión del chat
    # ------------------------------------------------------------------

    async def get_or_create_chat(self, chat_id: UUID | None) -> Chat:
        """Devuelve el chat existente o crea uno nuevo si chat_id es None o no existe.

        Siempre retorna un Chat válido persistido en DB.
        """
        if chat_id is not None:
            existing = await self._get_chat_by_id(chat_id)
            if existing is not None:
                self.logger.debug("chat recuperado: id=%s", chat_id)
                return existing
            self.logger.info("chat_id=%s no encontrado, se crea uno nuevo", chat_id)

        return await self._create_chat()

    async def _get_chat_by_id(self, chat_id: UUID) -> Chat | None:
        """Busca un chat por ID. Retorna None si no existe."""
        async with get_session() as session:
            chat = await session.get(Chat, chat_id)
        self.logger.debug("_get_chat_by_id: id=%s found=%s", chat_id, chat is not None)
        return chat

    async def _create_chat(self) -> Chat:
        """Crea y persiste un nuevo chat."""
        async with get_session() as session:
            chat = Chat(id=uuid4())
            session.add(chat)
            await session.commit()
            await session.refresh(chat)
        self.logger.info("chat creado: id=%s", chat.id)
        self.logger.debug("_create_chat: id=%s", chat.id)
        return chat

    async def touch_chat(self, chat_id: UUID) -> None:
        """Actualiza last_message_at del chat al momento actual."""
        now = datetime.now(timezone.utc)
        async with get_session() as session:
            await session.execute(update(Chat).where(Chat.id == chat_id).values(last_message_at=now))
            await session.commit()
        self.logger.debug("touch_chat: id=%s ts=%s", chat_id, now.isoformat())

    # ------------------------------------------------------------------
    # Gestión de mensajes
    # ------------------------------------------------------------------

    async def save_message(
        self,
        *,
        chat_id: UUID,
        role: ChatRole,
        content: str,
        message_type: MessageType = MESSAGE_TYPE_NORMAL,
        agent_run_id: UUID | None = None,
    ) -> ChatMessage:
        """Persiste un mensaje en el chat y actualiza last_message_at.

        Args:
            chat_id: ID del chat al que pertenece el mensaje.
            role: "user" o "assistant".
            content: Texto del mensaje.
            message_type: "normal", "error" o "cancelled".
            agent_run_id: ID del run asociado (solo para mensajes del asistente).
        """
        async with get_session() as session:
            msg = ChatMessage(
                id=uuid4(),
                chat_id=chat_id,
                role=role,
                message_type=message_type,
                content=content,
                agent_run_id=agent_run_id,
            )
            session.add(msg)
            await session.commit()
            await session.refresh(msg)

        await self.touch_chat(chat_id)
        self.logger.debug(
            "mensaje guardado: chat=%s role=%s type=%s run=%s",
            chat_id,
            role,
            message_type,
            agent_run_id,
        )
        return msg

    async def get_context_messages(
        self,
        chat_id: UUID,
        limit: int = 5,
    ) -> list[ChatMessage]:
        """Retorna los últimos `limit` mensajes NORMALES del chat para contexto del LLM.

        Los mensajes de tipo 'error' y 'cancelled' se excluyen deliberadamente
        para no contaminar el contexto conversacional del modelo.
        Los resultados vienen en orden cronológico (más antiguos primero).
        """
        async with get_session() as session:
            result = await session.execute(
                select(ChatMessage)
                .where(
                    ChatMessage.chat_id == chat_id,
                    ChatMessage.message_type == MESSAGE_TYPE_NORMAL,
                )
                .order_by(ChatMessage.ts.desc())
                .limit(limit)
            )
            messages = result.scalars().all()

        # Reordenar: de más antiguo a más reciente para inyectar en orden correcto
        ordered = list(reversed(messages))
        self.logger.debug(
            "get_context_messages: chat=%s mensajes=%d limit=%d",
            chat_id,
            len(ordered),
            limit,
        )
        return ordered

    async def get_all_messages(
        self,
        chat_id: UUID,
        limit: int = 100,
    ) -> list[ChatMessage]:
        """Retorna todos los mensajes del chat (incluidos error/cancelled) en orden cronológico.

        Útil para historial visible al usuario y para las tools internas del agente.
        """
        async with get_session() as session:
            result = await session.execute(
                select(ChatMessage).where(ChatMessage.chat_id == chat_id).order_by(ChatMessage.ts.asc()).limit(limit)
            )
            messages = list(result.scalars().all())
        self.logger.debug("get_all_messages: chat=%s count=%d limit=%d", chat_id, len(messages), limit)
        return messages

    # ------------------------------------------------------------------
    # Búsqueda y listado
    # ------------------------------------------------------------------

    async def search_chats(
        self,
        query: str,
        limit: int = 10,
    ) -> list[ChatSearchResult]:
        """Busca chats cuyos mensajes contengan el texto indicado (ILIKE).

        Retorna lista de dicts con id, preview del mensaje que hizo match y fecha.

        Nota: implementación con ILIKE. Para mayor escala considerar migrar a
        búsqueda full-text con tsvector/tsquery de PostgreSQL.
        """
        pattern = f"%{query}%"
        async with get_session() as session:
            result = await session.execute(
                select(ChatMessage)
                .where(ChatMessage.content.ilike(pattern))
                .order_by(ChatMessage.ts.desc())
                .limit(limit)
            )
            matches = result.scalars().all()

        seen_chats: dict[UUID, ChatSearchResult] = {}
        for msg in matches:
            if msg.chat_id not in seen_chats:
                preview = (
                    msg.content[:SEARCH_PREVIEW_MAX_LEN] + "..."
                    if len(msg.content) > SEARCH_PREVIEW_MAX_LEN
                    else msg.content
                )
                seen_chats[msg.chat_id] = ChatSearchResult(
                    chat_id=str(msg.chat_id),
                    preview=preview,
                    ts=msg.ts.isoformat(),
                    role=msg.role,
                )

        results = list(seen_chats.values())
        self.logger.debug("search_chats: query_len=%d encontrados=%d", len(query), len(results))
        return results

    async def list_recent_chats(self, limit: int = 20) -> list[Chat]:
        """Lista los chats más recientes ordenados por last_message_at desc."""
        async with get_session() as session:
            result = await session.execute(select(Chat).order_by(Chat.last_message_at.desc()).limit(limit))
            chats = list(result.scalars().all())
        self.logger.debug("list_recent_chats: total=%d limit=%d", len(chats), limit)
        return chats


@lru_cache(maxsize=1)
def get_chat_service() -> ChatService:
    """Singleton del ChatService."""
    return ChatService()
