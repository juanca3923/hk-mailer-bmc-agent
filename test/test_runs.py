"""Script de diagnóstico para las memory tools relacionadas con runs.

Llama a memory_get_current_task, memory_list_recent_runs y memory_get_run_events
y escribe la salida en test/output/runs_<timestamp>.log.

Uso:
    uv run python test/test_runs.py
    uv run python test/test_runs.py --run-id <uuid>
    uv run python test/test_runs.py --limit 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Agrega src/ al path para resolver imports del proyecto sin instalar el paquete
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Carga .env antes de importar cualquier módulo que use Settings
from dotenv import load_dotenv  # noqa: E402

load_dotenv(override=False)

from agent.internal_tools.memory_tools import MemoryTools  # noqa: E402
from database.engine import close_engine  # noqa: E402

_OUTPUT_DIR = Path(__file__).parent / "output"


def _memory_tool(name: str):  # noqa: ANN202
    return next(tool for tool in MemoryTools.get_tools() if tool.name == name)


def _section(title: str) -> str:
    sep = "=" * 70
    return f"\n{sep}\n{title}\n{sep}\n"


def _pretty(raw_json: str) -> str:
    """Re-formatea el JSON string que devuelven las tools para mejor legibilidad."""
    try:
        return json.dumps(json.loads(raw_json), indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return raw_json


async def run(limit: int, run_id: str | None) -> str:
    """Ejecuta las tres tools y devuelve el contenido completo del log."""
    lines: list[str] = []
    lines.append(f"Generado: {datetime.now().isoformat()}")
    lines.append(f"Configuración: limit={limit}, run_id={run_id or '(auto)'}")

    # ------------------------------------------------------------------ [1]
    lines.append(_section("[1] TAREA ACTIVA — memory_get_current_task()"))
    result_current = await _memory_tool("memory_get_current_task").ainvoke({})
    lines.append(_pretty(result_current))

    # ------------------------------------------------------------------ [2]
    lines.append(_section(f"[2] ÚLTIMAS RUNS — memory_list_recent_runs(limit={limit})"))
    result_runs = await _memory_tool("memory_list_recent_runs").ainvoke({"limit": limit})
    lines.append(_pretty(result_runs))

    # Determina el run_id a usar para la sección [3]
    target_run_id = run_id
    if target_run_id is None:
        try:
            runs_data = json.loads(result_runs)
            runs_list = runs_data.get("runs", [])
            if runs_list:
                target_run_id = runs_list[0]["id"]
        except (json.JSONDecodeError, KeyError, IndexError):
            pass

    # ------------------------------------------------------------------ [3]
    if target_run_id:
        lines.append(_section(f"[3] EVENTOS DE RUN — memory_get_run_events(run_id={target_run_id})"))
        result_events = await _memory_tool("memory_get_run_events").ainvoke({"run_id": target_run_id})
        lines.append(_pretty(result_events))
    else:
        lines.append(_section("[3] EVENTOS DE RUN"))
        lines.append("(No hay runs registradas; sección omitida)")

    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnóstico de memory tools de runs")
    parser.add_argument("--run-id", default=None, help="UUID del run a inspeccionar en [3]")
    parser.add_argument("--limit", type=int, default=5, help="Cuántas runs listar en [2] (default 5)")
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    try:
        content = await run(limit=args.limit, run_id=args.run_id)
    finally:
        await close_engine()

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = _OUTPUT_DIR / f"runs_{timestamp}.log"
    log_path.write_text(content, encoding="utf-8")
    print(f"Log escrito en {log_path}")


if __name__ == "__main__":
    asyncio.run(main())
