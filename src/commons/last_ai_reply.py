"""Extracción de la respuesta final visible al usuario desde mensajes de LangGraph."""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from commons.interceptor_helpers import InterceptorHelpers
from config import get_logger

logger = get_logger()


class ReplyExtractor:
    """Extrae la última respuesta del agente visible al usuario desde una lista de mensajes."""

    def from_messages(self, messages: list[BaseMessage]) -> str:
        """Retorna el texto final visible desde la salida de mensajes del grafo.

        Orden de preferencia:
          1. Última AIMessage con contenido no vacío y sin tool_calls (respuesta post-tools).
          2. Última AIMessage con cualquier contenido no vacío.
          3. Último ToolMessage con contenido textual no vacío.
          4. Fallback cuando ninguna condición aplica.
        """
        result = self.try_ai_no_tools(messages) or self.try_ai_any(messages) or self._try_tool_message(messages)
        if result:
            logger.debug("reply_extractor: respuesta extraída len=%d", len(result))
            return result
        logger.debug("reply_extractor: sin respuesta en %d mensajes, usando fallback", len(messages))
        return "(Sin respuesta del agente)"

    @staticmethod
    def ai_message_text(msg: AIMessage) -> str:
        """Texto visible del usuario a partir de ``content`` (str o bloques multimodal)."""
        return InterceptorHelpers.llm_message_body_text(msg.content)

    @staticmethod
    def try_ai_no_tools(messages: list[BaseMessage]) -> str | None:
        """Última AIMessage con contenido y sin tool_calls."""
        for msg in reversed(messages):
            if not isinstance(msg, AIMessage):
                continue
            text = ReplyExtractor.ai_message_text(msg)
            if not text or getattr(msg, "tool_calls", None):
                continue
            return text
        return None

    @staticmethod
    def try_ai_any(messages: list[BaseMessage]) -> str | None:
        """Última AIMessage con cualquier contenido no vacío."""
        for msg in reversed(messages):
            if not isinstance(msg, AIMessage):
                continue
            text = ReplyExtractor.ai_message_text(msg)
            if text:
                return text
        return None

    def _try_tool_message(self, messages: list[BaseMessage]) -> str | None:
        """Último ToolMessage con contenido textual (cuando el modelo devolvió content vacío)."""
        for msg in reversed(messages):
            if not isinstance(msg, ToolMessage) or not msg.content:
                continue
            text = self.tool_message_text(msg)
            if text and text.strip():
                return text
        return None

    @staticmethod
    def tool_message_text(msg: ToolMessage) -> str:
        """Normaliza el contenido de un ToolMessage a string."""
        if isinstance(msg.content, str):
            return msg.content
        if isinstance(msg.content, list):
            parts = [
                content.get("text", content) if isinstance(content, dict) else str(content) for content in msg.content
            ]
            return " ".join(str(p) for p in parts if p)
        return str(msg.content)
