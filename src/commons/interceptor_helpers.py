"""Helpers para los interceptors (callbacks) que persisten eventos del agente."""

from __future__ import annotations

from collections.abc import Iterator
from typing import cast

from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

from commons.utils import TextUtils
from type_defs.dicts.event_payloads import ToolResultLogEntry


class InterceptorHelpers:
    """Utilidades para extraer y serializar datos de callbacks de LangChain.

    Agrupa toda la lógica de parseo de mensajes, conteo de tokens y resumen
    de herramientas que usan los interceptors de ejecución del agente.
    """

    # ------------------------------------------------------------------
    # Constantes de truncado
    # ------------------------------------------------------------------

    RESULT_TRUNCATE_CHARS: int = 2000
    ERROR_TRUNCATE_CHARS: int = 2000
    MESSAGE_TRUNCATE_CHARS: int = 4000
    LLM_RESPONSE_TRUNCATE_CHARS: int = 8000
    LLM_END_LOG_PREVIEW_CHARS: int = 280

    # ------------------------------------------------------------------
    # Helpers de contenido de mensajes
    # ------------------------------------------------------------------

    @staticmethod
    def llm_message_body_text(content: str | list[str | dict[str, object]] | None) -> str:
        """Normaliza el content de un mensaje LangChain (str o bloques multimodal) a string."""
        parts: list[str] = []
        if content is None:
            return ""
        if isinstance(content, str):
            if content.strip():
                parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    parts.append(str(block.get("text", "")))
                elif isinstance(block, str) and block.strip():
                    parts.append(block)
        return " ".join(parts)

    def llm_message_reasoning_plus_content(self, msg: BaseMessage) -> str | None:
        """Combina reasoning_content (Ollama thinking) con content cuando existan ambos.

        Orden: razonamiento primero, luego contenido (separados por línea en blanco).
        """
        kwargs = msg.additional_kwargs or {}
        raw_reasoning: str | None = kwargs.get("reasoning_content")
        reasoning: str = str(raw_reasoning).strip() if raw_reasoning is not None else ""
        body = self.llm_message_body_text(msg.content)
        if reasoning and body:
            return f"{reasoning}\n\n{body}"
        if reasoning:
            return reasoning

        return body if body else None

    def extract_last_human_and_ai_messages(
        self,
        messages: list[list[BaseMessage]],
        limit: int = 4000,
    ) -> tuple[str | None, str | None]:
        """Extrae el último HumanMessage y el último AIMessage del historial de mensajes.

        Args:
            messages: Estructura list[list[BaseMessage]] que LangChain pasa a on_chat_model_start.
            limit: Límite de caracteres para truncar cada mensaje.

        Returns:
            Tupla (last_human, last_ai), None si no se encuentra el tipo.
        """
        last_human: str | None = None
        last_ai: str | None = None
        for msg in self.flatten_chat_model_message_batches(messages):
            last_human, last_ai = self._accumulate_last_human_and_ai(msg, limit, last_human, last_ai)
        return last_human, last_ai

    def _accumulate_last_human_and_ai(
        self,
        msg: BaseMessage,
        limit: int,
        last_human: str | None,
        last_ai: str | None,
    ) -> tuple[str | None, str | None]:
        """Actualiza el último humano/IA visto si ``msg`` es de esos tipos."""
        name = type(msg).__name__
        if name == "HumanMessage":
            body = self.llm_message_body_text(msg.content)
            if body:
                last_human = TextUtils.truncate(body, limit)
        elif name == "AIMessage":
            combined = self.llm_message_reasoning_plus_content(msg)
            if combined:
                last_ai = TextUtils.truncate(combined, limit)
        return last_human, last_ai

    @staticmethod
    def flatten_chat_model_message_batches(messages: list[list[BaseMessage]]) -> list[BaseMessage]:
        """Aplana list[list[BaseMessage]] que LangChain pasa a on_chat_model_start."""
        flat: list[BaseMessage] = []
        for batch in messages:
            if isinstance(batch, list):
                flat.extend(batch)
        return flat

    def extract_trailing_tool_results_for_llm_start(
        self,
        messages: list[list[BaseMessage]],
        limit: int = 4000,
    ) -> list[ToolResultLogEntry]:
        """ToolMessages consecutivos al final del historial que preceden al llamado al LLM.

        Vacío si este llm_start no va precedido de tools.
        """
        flat = self.flatten_chat_model_message_batches(messages)
        from_end: list[BaseMessage] = []
        for msg in reversed(flat):
            if type(msg).__name__ != "ToolMessage":
                break
            from_end.append(msg)
        from_end.reverse()

        rows: list[ToolResultLogEntry] = []
        for msg in from_end:
            raw = getattr(msg, "content", None)
            if raw is None:
                text: str | None = None
            elif isinstance(raw, str):
                clean_text = raw.strip()
                text = TextUtils.truncate(clean_text, limit) if clean_text else None
            else:
                text = TextUtils.truncate(str(raw), limit)
            row: ToolResultLogEntry = {
                "tool_name": getattr(msg, "name", None),
                "content": text,
            }
            tcid = getattr(msg, "tool_call_id", None)
            if tcid is not None:
                row["tool_call_id"] = str(tcid)
            rows.append(row)
        return rows

    def extract_llm_response_content(
        self,
        response: LLMResult,
        limit: int = 8000,
    ) -> str | None:
        """Extrae el texto de la respuesta del LLM desde LLMResult.

        Si hay reasoning_content, se incluye antes del content.
        """
        parts: list[str] = []
        for gen_list in response.generations:
            for gen in gen_list:
                msg: BaseMessage | None = getattr(gen, "message", None)
                if msg is None:
                    continue
                piece = self.llm_message_reasoning_plus_content(msg)
                if piece:
                    parts.append(piece)
        if not parts:
            return None
        return TextUtils.truncate(" ".join(parts), limit) or None

    @staticmethod
    def iter_llm_result_ai_messages(response: LLMResult) -> Iterator[BaseMessage]:
        """Recorre cada AIMessage dentro de LLMResult.generations."""
        for gen_list in response.generations:
            for gen in gen_list:
                msg: BaseMessage | None = getattr(gen, "message", None)
                if msg is not None:
                    yield msg

    def llm_message_is_effectively_empty(self, msg: BaseMessage) -> bool:
        """True si el mensaje no tiene texto, tool_calls ni reasoning_content."""
        if self.llm_message_body_text(getattr(msg, "content", None) or "") or getattr(msg, "tool_calls", []):
            return False
        add_kw = getattr(msg, "additional_kwargs", {})
        raw_rc = add_kw.get("reasoning_content")
        if raw_rc is not None and str(raw_rc).strip():
            return False
        return True

    def llm_result_has_suspicious_empty_message(self, response: LLMResult) -> bool:
        """True si alguna generación del LLMResult es un turno vacío (advertencia)."""
        return any(self.llm_message_is_effectively_empty(msg) for msg in self.iter_llm_result_ai_messages(response))

    def summarize_llm_end_for_logging(
        self,
        response: LLMResult,
        *,
        input_tokens: int,
        output_tokens: int,
        preview_limit: int = 280,
    ) -> str:
        """Una línea legible para logs a partir de LLMResult."""
        msgs = list(self.iter_llm_result_ai_messages(response))
        if not msgs:
            return "llm_end: (sin mensajes)"

        model, done_reason = self._llm_end_model_and_done_reason(msgs[0], response)
        tool_calls_total, reasoning_lens = self.llm_end_tool_calls_and_reasoning_lens(msgs)
        preview_fmt = self._llm_end_preview_repr(response, preview_limit)

        parts = [
            f"model={model!r}",
            f"n_messages={len(msgs)}",
            f"in={input_tokens}",
            f"out={output_tokens}",
            f"tool_calls={tool_calls_total}",
        ]
        reasoning_part = self.llm_end_reasoning_chars_part(reasoning_lens)
        if reasoning_part is not None:
            parts.append(reasoning_part)
        if done_reason is not None:
            parts.append(f"done_reason={done_reason!r}")
        parts.append(f"preview={preview_fmt}")

        return "llm_end: " + " ".join(parts)

    def _llm_end_model_and_done_reason(
        self,
        first: BaseMessage,
        response: LLMResult,
    ) -> tuple[object, object]:
        meta = getattr(first, "response_metadata", None) or {}
        gi = self.first_generation_info(response) or {}
        model = meta.get("model_name") or meta.get("model") or gi.get("model_name") or gi.get("model")
        done_reason = meta.get("done_reason") or gi.get("done_reason")
        return model, done_reason

    @staticmethod
    def llm_end_tool_calls_and_reasoning_lens(
        msgs: list[BaseMessage],
    ) -> tuple[int, list[int]]:
        tool_calls_total = 0
        reasoning_lens: list[int] = []
        for message in msgs:
            tool_calls_total += len(getattr(message, "tool_calls", None) or [])
            add_kw = getattr(message, "additional_kwargs", None) or {}
            reasoning_content: str | None = add_kw.get("reasoning_content")
            if reasoning_content is not None and str(reasoning_content).strip():
                reasoning_lens.append(len(str(reasoning_content)))
        return tool_calls_total, reasoning_lens

    @staticmethod
    def llm_end_reasoning_chars_part(reasoning_lens: list[int]) -> str | None:
        if not reasoning_lens:
            return None
        if len(reasoning_lens) == 1:
            return f"reasoning_chars={reasoning_lens[0]}"
        return f"reasoning_chars={reasoning_lens}"

    def _llm_end_preview_repr(self, response: LLMResult, preview_limit: int) -> str:
        piece = self.extract_llm_response_content(response, limit=preview_limit)
        preview = TextUtils.truncate(piece or "", preview_limit)
        return repr(preview) if preview else "None"

    def extract_usage_tokens(self, response: LLMResult) -> tuple[int, int]:
        """Extrae input_tokens y output_tokens del LLMResult (Ollama: prompt_eval_count/eval_count)."""
        inp, out = 0, 0
        if not getattr(response, "generations", None):
            return inp, out
        for gen_list in response.generations:
            for gen in gen_list:
                msg = getattr(gen, "message", None)
                if msg is None:
                    continue
                usage_meta = self.as_dict(getattr(msg, "usage_metadata", None))
                gen_info = self.as_dict(getattr(gen, "generation_info", None))
                resp_meta = self.as_dict(getattr(msg, "response_metadata", None))
                merged: dict[str, object] = {**resp_meta, **gen_info, **usage_meta}
                inp += int(cast("int | str", merged.get("input_tokens") or merged.get("prompt_eval_count") or 0))
                out += int(cast("int | str", merged.get("output_tokens") or merged.get("eval_count") or 0))
        return inp, out

    def tool_result_summary(self, output: object, limit: int = 2000) -> str | dict[str, object] | None:
        """Resumen acotado del resultado de una tool para guardar en payload."""
        if output is None:
            return None
        if isinstance(output, dict):
            summary = self.tool_result_summary_from_dict(output)
        elif isinstance(output, list):
            summary = self.tool_result_summary_from_list(output, limit)
        else:
            summary = TextUtils.truncate(str(output), limit)
        return summary

    # ------------------------------------------------------------------
    # Helpers privados de implementación interna
    # ------------------------------------------------------------------

    @staticmethod
    def tool_result_summary_from_dict(output: dict[str, object]) -> str | dict[str, object]:
        if "structured_content" in output:
            return cast("str | dict[str, object]", output["structured_content"])
        return dict(list(output.items())[:10])

    @staticmethod
    def tool_result_summary_from_list(output: list[object], limit: int) -> str:
        texts: list[str] = []
        for item in output:
            if isinstance(item, dict) and "text" in item:
                texts.append(str(item["text"]))
            elif isinstance(item, str):
                texts.append(item)
        to_truncate = " ".join(texts) if texts else str(output)
        return TextUtils.truncate(to_truncate, limit)

    @staticmethod
    def first_generation_info(response: LLMResult) -> dict[str, object] | None:
        """Retorna el primer generation_info disponible en las generaciones del LLMResult."""
        for gen_list in response.generations:
            for gen in gen_list:
                gi = getattr(gen, "generation_info", None)
                if isinstance(gi, dict):
                    return gi
        return None

    @staticmethod
    def as_dict(value: object) -> dict[str, object]:
        """Retorna value si es dict, de lo contrario un dict vacío."""
        return value if isinstance(value, dict) else {}
