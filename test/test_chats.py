"""Script de diagnóstico para las memory tools relacionadas con chats.

Llama a memory_search_chats y memory_get_chat_messages, y además muestra
los mensajes del chat que el checkpointer gestionaría como historial activo.

Escribe la salida en test/output/chats_<timestamp>.log.

Uso:
    uv run python test/test_chats.py
    uv run python test/test_chats.py --query "nginx"
    uv run python test/test_chats.py --chat-id <uuid>
    uv run python test/test_chats.py --chat-id <uuid> --limit 30
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

# Agrega src/ al path para resolver imports del proyecto sin instalar el paquete
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Carga .env antes de importar cualquier módulo que use Settings
from dotenv import load_dotenv  # noqa: E402

load_dotenv(override=False)

from agent.internal_tools.memory_tools import (  # noqa: E402
    memory_get_chat_messages,
    memory_search_chats,
)
from commons.runner import MessageConverter  # noqa: E402
from database.engine import close_engine  # noqa: E402
from services.chat_service import get_chat_service  # noqa: E402

_OUTPUT_DIR = Path(__file__).parent / "output"


def _section(title: str) -> str:
    sep = "=" * 70
    return f"\n{sep}\n{title}\n{sep}\n"


def _pretty(raw_json: str) -> str:
    """Re-formatea el JSON string que devuelven las tools para mejor legibilidad."""
    try:
        return json.dumps(json.loads(raw_json), indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return raw_json


async def _build_checkpointer_context_section(chat_id: str, limit: int) -> str:
    """Muestra los mensajes del chat como los vería el checkpointer de LangGraph.

    El checkpointer rehidrata el hilo completo por thread_id; aquí mostramos
    los mensajes de BD convertidos al formato LangChain para inspección.
    """
    lines: list[str] = []
    try:
        chat_uuid = UUID(chat_id)
    except ValueError:
        return f"chat_id inválido para obtener contexto: '{chat_id}'"

    chat_svc = get_chat_service()
    db_messages = await chat_svc.get_context_messages(chat_uuid, limit=limit)
    langchain_messages = MessageConverter.to_langchain(db_messages)

    lines.append(
        "NOTA: con el checkpointer activo, LangGraph rehidrata automáticamente "
        "el hilo completo usando thread_id=chat_id."
    )
    lines.append(f"Mensajes en BD: {len(db_messages)}")
    lines.append(f"Mensajes como LangChain (preview): {len(langchain_messages)}")
    lines.append("")

    if not langchain_messages:
        lines.append("(Sin mensajes en BD — chat nuevo o vacío)")
        return "\n".join(lines)

    context_repr = [
        {
            "type": type(msg).__name__,
            "content": msg.content if isinstance(msg.content, str) else str(msg.content),
        }
        for msg in langchain_messages
    ]
    lines.append(json.dumps(context_repr, indent=2, ensure_ascii=False))
    return "\n".join(lines)


async def run(query: str, chat_id: str | None, limit: int) -> str:
    """Ejecuta las tools y construye el contenido completo del log."""
    lines: list[str] = []
    lines.append(f"Generado: {datetime.now().isoformat()}")
    lines.append(f"Configuración: query={query!r}, chat_id={chat_id or '(auto)'}, limit={limit}")

    # ------------------------------------------------------------------ [1]
    lines.append(_section(f'[1] BÚSQUEDA DE CHATS — memory_search_chats(query="{query}")'))
    result_search = await memory_search_chats.ainvoke({"query": query})
    lines.append(_pretty(result_search))

    # Determina el chat_id a usar para [2] y [3]
    target_chat_id = chat_id
    if target_chat_id is None:
        try:
            search_data = json.loads(result_search)
            found = search_data.get("found", [])
            if found:
                target_chat_id = found[0]["chat_id"]
        except (json.JSONDecodeError, KeyError, IndexError):
            pass

    # ------------------------------------------------------------------ [2]
    if target_chat_id:
        lines.append(
            _section(
                f"[2] MENSAJES DEL CHAT — memory_get_chat_messages(chat_id={target_chat_id}, limit={limit})"
            )
        )
        result_messages = await memory_get_chat_messages.ainvoke(
            {"chat_id": target_chat_id, "limit": limit}
        )
        lines.append(_pretty(result_messages))
    else:
        lines.append(_section("[2] MENSAJES DEL CHAT"))
        lines.append("(No se encontró ningún chat; sección omitida)")

    # ------------------------------------------------------------------ [3]
    lines.append(
        _section(
            "[3] CONTEXTO LLM (preview) — mensajes BD → formato LangChain "
            "(el checkpointer gestiona el historial real en tiempo de ejecución)"
        )
    )
    if target_chat_id:
        lines.append(await _build_checkpointer_context_section(target_chat_id, limit))
    else:
        lines.append("(Sin chat_id disponible; sección omitida)")

    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnóstico de memory tools de chats")
    parser.add_argument(
        "--query",
        default="",
        help='Texto a buscar en historial de chats (default: "" muestra todos)',
    )
    parser.add_argument(
        "--chat-id",
        default=None,
        help="UUID del chat; si se pasa, va directo a [2] y [3] sin buscar",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Número de mensajes a cargar en [2] y [3] (default 20)",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    try:
        content = await run(query=args.query, chat_id=args.chat_id, limit=args.limit)
    finally:
        await close_engine()

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = _OUTPUT_DIR / f"chats_{timestamp}.log"
    log_path.write_text(content, encoding="utf-8")
    print(f"Log escrito en {log_path}")


if __name__ == "__main__":
    asyncio.run(main())
