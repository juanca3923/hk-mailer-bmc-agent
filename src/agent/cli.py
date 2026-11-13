"""CLI para AgentForge."""

from __future__ import annotations

import asyncio
from uuid import UUID

from agent.a2a_peers import get_a2a_registry_from_graph
from agent.agent import build_agent
from agent.runtime.runner import get_agent_runner
from config import Settings, get_logger, get_user_logger
from database.engine import ensure_schema
from exception import AgentError
from services import get_agent_events_service
from type_defs import StatusAgent


class AgentCLI:
    """CLI para AgentForge.

    Cada sesión CLI crea un chat nuevo en DB. El contexto de la conversación
    se carga desde la DB en cada turno (igual que en el modo HTTP).

    El protocolo A2A como **servidor** (Agent Card y JSON-RPC) solo está disponible
    al ejecutar ``agent-forge-http`` (cliente HTTP). En consola sí puedes usar
    **cliente** A2A hacia otros agentes vía ``A2A_PEER_URLS`` y las tools internas
    ``a2a_list_remote_agents`` / ``a2a_send_to_remote`` del mismo grafo.
    """

    # Upper bound for one REPL line before passing to the agent (CWE-20: bounded stdin).
    CLI_MAX_USER_INPUT_CHARS = 32_000
    # First printable ASCII code point (strip C0 controls except tab).
    _MIN_PRINTABLE_ORD = 32

    @staticmethod
    def sanitize_repl_user_input(raw_line: str) -> str:
        """Sanitize a single line read from stdin before agent processing.

        Parameters
        ----------
        raw_line : str
            Raw text returned by ``input()`` (or equivalent).

        Returns
        -------
        str
            Stripped text without NUL or other C0 control characters, capped in length.
        """
        text = raw_line.strip()
        if not text:
            return ""
        cleaned = "".join(
            character for character in text if ord(character) >= AgentCLI._MIN_PRINTABLE_ORD or character == "\t"
        )
        if len(cleaned) > AgentCLI.CLI_MAX_USER_INPUT_CHARS:
            cleaned = cleaned[: AgentCLI.CLI_MAX_USER_INPUT_CHARS]
        return cleaned

    @staticmethod
    def read_repl_user_input(prompt: str = "> ") -> str:
        """Read one REPL line from stdin and return sanitized text (CWE-20).

        Parameters
        ----------
        prompt : str
            Prompt shown to the user.

        Returns
        -------
        str
            Sanitized user input safe to pass to the agent.
        """
        raw_line = input(prompt)  # NOSONAR — sanitizado en sanitize_repl_user_input antes de devolver
        return AgentCLI.sanitize_repl_user_input(raw_line)

    def __init__(self) -> None:
        self.settings = Settings.load()
        self.logger = get_logger()
        self.user_logger = get_user_logger()
        self.status: StatusAgent = "DOWN"
        # Se asigna al iniciar el REPL; None hasta entonces
        self.chat_id: UUID | None = None

    def _log_remote_a2a_peers_if_any(self, graph: object) -> None:
        """Si hay ``A2A_PEER_URLS``, lista peers ya cargados por ``build_agent``."""
        if not self.settings.normalized_a2a_peer_configs():
            return
        registry = get_a2a_registry_from_graph(graph)
        if registry is None:
            return
        peers = registry.list_peers()
        if not peers:
            self.user_logger.info(
                "[A2A] Había URLs en A2A_PEER_URLS pero no se pudo cargar ningún Agent Card. "
                "Revisa conectividad HTTP y assistant_id remoto.\n"
            )
            return
        self.user_logger.info("[A2A] Agentes remotos configurados (outbound, tools del grafo):")
        for agent_remote_peer in peers:
            self.user_logger.info(
                "  [%d] %s — %s (assistant_id=%s)",
                agent_remote_peer.index,
                agent_remote_peer.name,
                agent_remote_peer.base_url,
                agent_remote_peer.assistant_id,
            )
        self.user_logger.info(
            "Puedes pedir al agente que use las herramientas a2a_list_remote_agents / "
            "a2a_send_to_remote para hablar con ellos por el estándar A2A.\n"
        )

    async def _run_turn(self, user_input: str, graph: object) -> str:
        """Ejecuta un turno no-streaming y retorna la respuesta del agente.

        Delega toda la lógica de persistencia a AgentRunner.
        """
        self.status = "DOING_TASK"
        runner = get_agent_runner()
        result = await runner.run_agent_turn(
            user_message=user_input,
            graph=graph,
            chat_id=self.chat_id,
            events_service=get_agent_events_service(),
        )
        self.chat_id = result.chat_id
        return result.reply

    async def _stream_turn(self, user_input: str, graph: object) -> None:
        """Versión streaming del turno: imprime tokens a medida que llegan.

        Delega en ``AgentRunner.stream_agent_turn`` (misma lógica que HTTP SSE).
        """
        self.status = "DOING_TASK"
        runner = get_agent_runner()
        self.user_logger.info("\n[agente] Streaming de respuesta...\n")
        async for event in runner.stream_agent_turn(
            user_message=user_input,
            graph=graph,
            chat_id=self.chat_id,
            events_service=get_agent_events_service(),
        ):
            if event["type"] == "chunk":
                print(event["text"], end="", flush=True)
            elif event["type"] == "done":
                self.chat_id = UUID(event["chat_id"])
                print("\n", flush=True)
            elif event["type"] == "error":
                self.user_logger.error("\n[error] %s\n", event["detail"])

    async def _repl_loop(self, graph: object) -> None:
        """Bucle interactivo hasta EOF o comando de salida."""
        self.user_logger.info("Agente listo. Escribe tu pregunta. (salir: Ctrl+D o 'exit')\n")
        self.logger.info("sesión CLI iniciada (chat_id se asignará en el primer turno)")
        self._log_remote_a2a_peers_if_any(graph)

        while True:
            self.status = "UP"
            try:
                user_input = self.read_repl_user_input()
            except EOFError:
                self.user_logger.info("\nSaliendo.")
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                self.user_logger.info("Saliendo.")
                break

            if self.settings.stream:
                await self._stream_turn(user_input, graph)
            else:
                self.user_logger.info("\n[agente] Pensando...\n")
                reply = await self._run_turn(user_input, graph)
                self.user_logger.info("\n%s\n", reply)

            self.logger.debug("turno completado: chat=%s", self.chat_id)

    async def run_repl(self) -> int:
        """Ejecuta el REPL de AgentForge."""
        exit_code = 0
        try:
            await ensure_schema()
            async with build_agent(self.settings) as graph:
                await self._repl_loop(graph)
        except FileNotFoundError as e:
            self.logger.error("Error: no se encontró el system prompt.\n- %s\n", e)
            self.user_logger.error("Error: no se encontró el system prompt.\n- %s\n", e)
            self.user_logger.error("Verifica que exista `system.promt.md` en la raíz de `agent_linux_server/`.")
            exit_code = 2
        except AgentError as e:
            self.logger.exception("Error al iniciar el agente (Ollama/MCP/config).")
            self.user_logger.error("Error al iniciar el agente (Ollama/MCP/config).")
            self.user_logger.error("- %s: %s", type(e).__name__, e)
            self.user_logger.error("\nChecklist:")
            self.user_logger.error("- Ollama corriendo y accesible (ver `OLLAMA_BASE_URL`).")
            self.user_logger.error("- MCP accesible (ver `MCP_URLS`, debe terminar en `/mcp`).")
            self.user_logger.error(
                "- Si usas A2A_PEER_URLS: cada peer como `url_base|assistant_id` del remoto "
                "(comas); URLs alcanzables y assistant_id correcto en el peer."
            )
            exit_code = 2
        return exit_code


# Aliases at module level so tests can import without instantiating AgentCLI.
CLI_MAX_USER_INPUT_CHARS = AgentCLI.CLI_MAX_USER_INPUT_CHARS
sanitize_repl_user_input = AgentCLI.sanitize_repl_user_input


def main() -> int:
    """Punto de entrada del CLI."""
    cli = AgentCLI()
    try:
        return asyncio.run(cli.run_repl())
    except KeyboardInterrupt:
        cli.user_logger.info("\nInterrumpido.")
        return 130
