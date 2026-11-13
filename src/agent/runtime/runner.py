"""AgentRunner: orquesta un turno completo de conversación.

Toda la lógica de persistencia, invocación del grafo y ciclo de vida de un turno
vive aquí, de modo que CLI y HTTP usen exactamente el mismo flujo.

Con el checkpointer de LangGraph activo, el historial de conversación lo gestiona
el grafo; el runner solo necesita guardar los mensajes en BD (trazabilidad) y
pasar el mensaje nuevo al grafo con el thread_id del chat.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from functools import lru_cache
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from langchain_core.callbacks import AsyncCallbackHandler, BaseCallbackHandler
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler

from agent.interceptors.agent_run_callback import AgentRunCallbackHandler
from agent.observability.interceptor_helpers import InterceptorHelpers
from agent.observability.langfuse_tracing import ensure_langfuse_tracing_client
from agent.runtime.last_ai_reply import ReplyExtractor
from commons.text.utils import TextUtils
from config import get_logger
from config.settings import Settings
from database.models import ChatMessage
from exception import AgentError
from services.persistence.agent_events_service import AgentEventsService
from services.persistence.agent_runs_service import get_agent_runs_service
from services.persistence.chat_service import get_chat_service
from type_defs.enums.domain_literals import (
    MESSAGE_TYPE_CANCELLED,
    MESSAGE_TYPE_ERROR,
    MESSAGE_TYPE_NORMAL,
    ROLE_ASSISTANT,
    ROLE_USER,
)
from type_defs.models.agent.agent_turn import AgentTurnResult, ErrorKind, TurnContext
from type_defs.models.agent.chat_stream import (
    ChatStreamChunkEvent,
    ChatStreamDoneEvent,
    ChatStreamErrorEvent,
    ChatStreamServerEvent,
)

logger = get_logger()


class MessageConverter:
    """Convierte mensajes de la BD a objetos LangChain y viceversa."""

    @staticmethod
    def to_langchain(db_messages: list[ChatMessage]) -> list[BaseMessage]:
        """Convierte ChatMessage de BD a HumanMessage / AIMessage de LangChain."""
        result: list[BaseMessage] = []
        for msg in db_messages:
            if msg.role == ROLE_USER:
                result.append(HumanMessage(content=msg.content))
            else:
                result.append(AIMessage(content=msg.content))
        return result


class AgentRunner:
    """Orquesta un turno completo de conversación entre usuario y agente.

    Responsabilidades:
      - Crear/recuperar el chat en BD.
      - Persistir el mensaje del usuario y la respuesta del agente.
      - Crear y cerrar el AgentRun para trazabilidad y métricas.
      - Invocar el grafo LangGraph con thread_id y callbacks.

    El historial de conversación lo gestiona el checkpointer de LangGraph;
    aquí solo se persiste para trazabilidad y entrenamiento futuro.
    """

    MSG_CANCELLED = "Cancelado por el usuario."
    MSG_ERROR_PREFIX = "Error del sistema: "

    # ------------------------------------------------------------------
    # API pública: preparación y finalización de turnos
    # ------------------------------------------------------------------
    @staticmethod
    async def prepare_turn(
        *,
        user_message: str,
        chat_id: UUID | None,
    ) -> TurnContext:
        """Prepara el contexto de un turno: crea chat, persiste mensaje y crea run.

        Pasos:
          1. Obtiene o crea el chat en BD.
          2. Persiste el mensaje del usuario (trazabilidad).
          3. Crea el AgentRun en BD.

        El historial de conversación viene del checkpointer, no de aquí.
        """
        chat_svc = get_chat_service()
        runs_svc = get_agent_runs_service()

        chat = await chat_svc.get_or_create_chat(chat_id)
        logger.debug("prepare_turn: chat=%s user_message_len=%d", chat.id, len(user_message))

        await chat_svc.save_message(
            chat_id=chat.id,
            role=ROLE_USER,
            content=user_message,
            message_type=MESSAGE_TYPE_NORMAL,
        )

        run_id = uuid4()
        await runs_svc.create_run(
            agent_run_id=run_id,
            user_message=user_message,
            chat_id=chat.id,
        )
        logger.info("turno iniciado: run=%s chat=%s message_len=%d", run_id, chat.id, len(user_message))

        return TurnContext(
            chat_id=chat.id,
            run_id=run_id,
            messages=[HumanMessage(content=user_message)],
        )

    @staticmethod
    async def finish_turn_success(*, ctx: TurnContext, reply: str) -> AgentTurnResult:
        """Persiste el resultado exitoso del turno y retorna AgentTurnResult."""
        chat_svc = get_chat_service()
        runs_svc = get_agent_runs_service()

        await runs_svc.finish_run_success(agent_run_id=ctx.run_id, final_reply=reply)
        await chat_svc.save_message(
            chat_id=ctx.chat_id,
            role=ROLE_ASSISTANT,
            content=reply,
            message_type=MESSAGE_TYPE_NORMAL,
            agent_run_id=ctx.run_id,
        )
        logger.info(
            "turno éxito: run=%s chat=%s reply_len=%d duración=%.1fs",
            ctx.run_id,
            ctx.chat_id,
            len(reply),
            time.monotonic() - ctx.started_at,
        )
        return AgentTurnResult(reply=reply, chat_id=ctx.chat_id, run_id=ctx.run_id, status="success")

    async def finish_turn_cancelled(self, *, ctx: TurnContext) -> AgentTurnResult:
        """Persiste la cancelación del turno y retorna AgentTurnResult."""
        chat_svc = get_chat_service()
        runs_svc = get_agent_runs_service()

        await runs_svc.finish_run_cancelled(agent_run_id=ctx.run_id)
        await chat_svc.save_message(
            chat_id=ctx.chat_id,
            role=ROLE_ASSISTANT,
            content=self.MSG_CANCELLED,
            message_type=MESSAGE_TYPE_CANCELLED,
            agent_run_id=ctx.run_id,
        )
        logger.info(
            "turno cancelado: run=%s chat=%s duración=%.1fs",
            ctx.run_id,
            ctx.chat_id,
            time.monotonic() - ctx.started_at,
        )
        return AgentTurnResult(
            reply=self.MSG_CANCELLED,
            chat_id=ctx.chat_id,
            run_id=ctx.run_id,
            status="cancelled",
        )

    async def finish_turn_error(
        self,
        *,
        ctx: TurnContext,
        error_detail: str,
        error_kind: ErrorKind = None,
    ) -> AgentTurnResult:
        """Persiste el error del turno y retorna AgentTurnResult."""
        chat_svc = get_chat_service()
        runs_svc = get_agent_runs_service()

        await runs_svc.finish_run_error(agent_run_id=ctx.run_id, error_text=error_detail)
        error_content = f"{self.MSG_ERROR_PREFIX}{error_detail}"
        await chat_svc.save_message(
            chat_id=ctx.chat_id,
            role=ROLE_ASSISTANT,
            content=error_content,
            message_type=MESSAGE_TYPE_ERROR,
            agent_run_id=ctx.run_id,
        )
        logger.error(
            "turno error: run=%s chat=%s kind=%s duración=%.1fs detail=%s",
            ctx.run_id,
            ctx.chat_id,
            error_kind,
            time.monotonic() - ctx.started_at,
            TextUtils.truncate(error_detail, 200),
        )
        return AgentTurnResult(
            reply=error_content,
            chat_id=ctx.chat_id,
            run_id=ctx.run_id,
            status="error",
            error_kind=error_kind,
        )

    async def run_agent_turn(
        self,
        *,
        user_message: str,
        graph: object,
        chat_id: UUID | None = None,
        callbacks: list[AsyncCallbackHandler] | None = None,
        events_service: AgentEventsService | None = None,
    ) -> AgentTurnResult:
        """Ejecuta un turno completo de conversación con el agente (modo no-streaming).

        Flujo:
          1. Prepara el contexto (prepare_turn).
          2. Invoca el grafo con thread_id y callbacks.
          3. Persiste el resultado y retorna AgentTurnResult.

        Args:
            user_message: Texto enviado por el usuario.
            graph: Grafo compilado de LangGraph (resultado de build_agent).
            chat_id: ID del chat existente, o None para crear uno nuevo.
            callbacks: Callbacks de LangChain adicionales (opcional).
            events_service: Si se informa, registra eventos (llm_end, tokens, etc.)
                asociados al run_id del turno.
        """
        ctx = await self.prepare_turn(user_message=user_message, chat_id=chat_id)
        settings = Settings.load()
        config = self.build_graph_invoke_config(ctx, events_service, callbacks, settings)

        logger.debug("ainvoke: thread_id=%s run=%s", ctx.chat_id, ctx.run_id)
        result: AgentTurnResult | None = None

        try:
            graph_output = await graph.ainvoke({"messages": ctx.messages}, config=config)  # type: ignore[attr-defined]
            reply = ReplyExtractor().from_messages(graph_output.get("messages", []))
            return await self.finish_turn_success(ctx=ctx, reply=reply)

        except asyncio.CancelledError:
            result = await self.finish_turn_cancelled(ctx=ctx)

        except AgentError as exc:
            result = await self.finish_turn_error(ctx=ctx, error_detail=str(exc))

        # pylint: disable-next=broad-exception-caught
        except Exception as exc:  # noqa: BLE001 — safety-net: garantiza persistencia ante cualquier fallo inesperado
            error_kind: ErrorKind = "llm_provider" if self.is_llm_provider_error(exc) else "functional"
            if error_kind == "llm_provider":
                self.log_llm_provider_error(ctx, exc, settings)
            else:
                logger.exception("run error inesperado: id=%s", ctx.run_id)
            result = await self.finish_turn_error(ctx=ctx, error_detail=repr(exc), error_kind=error_kind)

        return result

    async def stream_agent_turn(
        self,
        *,
        user_message: str,
        graph: object,
        chat_id: UUID | None = None,
        callbacks: list[AsyncCallbackHandler] | None = None,
        events_service: AgentEventsService | None = None,
    ) -> AsyncIterator[ChatStreamServerEvent]:
        """Ejecuta un turno en modo streaming (misma persistencia que ``run_agent_turn``).

        Emite eventos ``chunk`` (texto delta), luego ``done`` (éxito o cancelación) o
        ``error`` (fallo controlado tras ``finish_turn_error``).
        """
        ctx = await self.prepare_turn(user_message=user_message, chat_id=chat_id)
        settings = Settings.load()
        config = self.build_graph_invoke_config(ctx, events_service, callbacks, settings)

        logger.debug("astream: thread_id=%s run=%s", ctx.chat_id, ctx.run_id)

        terminal: ChatStreamDoneEvent | ChatStreamErrorEvent | None = None
        streamed_parts: list[str] = []
        try:
            async for chunk_event in self.iter_agent_message_chunks(graph, ctx.messages, config):
                streamed_parts.append(chunk_event["text"])
                yield chunk_event

            reply = "".join(streamed_parts).strip() or "(Sin respuesta del agente)"
            result = await self.finish_turn_success(ctx=ctx, reply=reply)
            terminal = ChatStreamDoneEvent(
                type="done",
                chat_id=str(result.chat_id),
                run_id=str(result.run_id),
                status="success",
                reply=result.reply,
            )

        except asyncio.CancelledError:
            result = await self.finish_turn_cancelled(ctx=ctx)
            terminal = ChatStreamDoneEvent(
                type="done",
                chat_id=str(result.chat_id),
                run_id=str(result.run_id),
                status="cancelled",
                reply=result.reply,
            )

        except AgentError as exc:
            await self.finish_turn_error(ctx=ctx, error_detail=str(exc))
            terminal = ChatStreamErrorEvent(type="error", detail=str(exc))

        # pylint: disable-next=broad-exception-caught
        except Exception as exc:  # noqa: BLE001 — safety-net: garantiza persistencia ante cualquier fallo inesperado
            error_kind: ErrorKind = "llm_provider" if self.is_llm_provider_error(exc) else "functional"
            if error_kind == "llm_provider":
                self.log_llm_provider_error(ctx, exc, settings)
            else:
                logger.exception("run error inesperado: id=%s", ctx.run_id)
            await self.finish_turn_error(ctx=ctx, error_detail=repr(exc), error_kind=error_kind)
            terminal = ChatStreamErrorEvent(type="error", detail=repr(exc))

        finally:
            if terminal is not None:
                yield terminal

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    @staticmethod
    async def iter_agent_message_chunks(
        graph: object,
        messages: list[BaseMessage],
        config: dict[str, object],
    ) -> AsyncIterator[ChatStreamChunkEvent]:
        """Emite eventos ``chunk`` por cada fragmento de texto del modelo."""
        helpers = InterceptorHelpers()
        async for chunk, _meta in graph.astream(  # type: ignore[attr-defined]
            {"messages": messages},
            config,
            stream_mode="messages",
        ):
            if isinstance(chunk, AIMessageChunk):
                text = helpers.llm_message_body_text(chunk.content)
                if text:
                    yield ChatStreamChunkEvent(type="chunk", text=text)

    @staticmethod
    def build_graph_invoke_config(
        ctx: TurnContext,
        events_service: AgentEventsService | None,
        callbacks: list[AsyncCallbackHandler] | None,
        settings: Settings,
    ) -> dict[str, object]:
        """Construye el dict ``config`` para ``ainvoke`` / ``astream`` del grafo."""
        merged_callbacks: list[BaseCallbackHandler] = []
        if events_service is not None:
            merged_callbacks.extend(AgentRunCallbackHandler.build_callbacks(ctx.run_id, events_service))
        if settings.langfuse_tracing_ready:
            ensure_langfuse_tracing_client(settings)

            merged_callbacks.append(LangfuseCallbackHandler(public_key=settings.langfuse_public_key.strip()))
        if callbacks:
            merged_callbacks.extend(callbacks)

        invoke_config: dict[str, object] = {
            "configurable": {"thread_id": str(ctx.chat_id)},
        }
        if merged_callbacks:
            invoke_config["callbacks"] = merged_callbacks
        return invoke_config

    @staticmethod
    def is_llm_provider_error(exc: BaseException) -> bool:
        """True si el fallo parece provenir del cliente del proveedor LLM."""
        cls = type(exc)
        mod = getattr(cls, "__module__", "") or ""
        if (
            (cls.__name__ == "ResponseError" and mod.startswith("ollama"))
            or mod.startswith("openai")
            or mod.startswith("anthropic")
        ):
            return True
        return False

    @staticmethod
    def log_llm_provider_error(ctx: TurnContext, exc: BaseException, settings: Settings) -> None:
        """Loguea detalles del proveedor LLM para diagnosticar fallos de stream/HTTP."""
        provider = settings.llm_provider
        if provider == "openai":
            model = settings.openai_model
            endpoint = (settings.openai_base_url or "").strip() or "(default OpenAI)"
        elif provider == "anthropic":
            model = settings.anthropic_model
            endpoint = "(Anthropic API)"
        else:
            model = settings.ollama_model
            endpoint = settings.ollama_base_url
        # Only the host is logged: a configured URL may embed credentials.
        endpoint = (urlsplit(endpoint).hostname or "(unknown)") if "://" in endpoint else endpoint
        stream = settings.stream
        status = getattr(exc, "status_code", None)
        logger.exception(
            "LLM provider error (%s): run=%s chat=%s model=%r endpoint=%r stream=%r "
            "messages_in_turn=%d status_code=%r error=%s",
            provider,
            ctx.run_id,
            ctx.chat_id,
            model,
            endpoint,
            stream,
            len(ctx.messages),
            status,
            TextUtils.truncate(str(exc), 200),
        )


@lru_cache(maxsize=1)
def get_agent_runner() -> AgentRunner:
    """Singleton de AgentRunner."""
    return AgentRunner()
