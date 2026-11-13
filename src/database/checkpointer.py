"""Gestión del ciclo de vida del checkpointer de LangGraph con Postgres."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from config import Settings, get_logger

logger = get_logger()


class CheckpointerManager:
    """Gestiona el ciclo de vida del AsyncPostgresSaver y su pool de psycopg3.

    Usa AsyncPostgresSaver.from_conn_string() que internamente crea y gestiona
    un pool de conexiones con psycopg3. Diseñado para usarse como context manager
    desde build_agent en el arranque del agente.
    """

    @classmethod
    @asynccontextmanager
    async def build(cls, settings: Settings) -> AsyncIterator[AsyncPostgresSaver]:
        """Context manager que construye y entrega un AsyncPostgresSaver listo para usar.

        Pasos:
          1. Abre el saver via from_conn_string (psycopg3 gestiona el pool internamente).
          2. Llama a saver.setup() para crear las tablas de checkpoints si no existen.
          3. Entrega el saver; al salir del contexto psycopg3 cierra el pool.

        Args:
            settings: Configuración del proyecto (necesita asyncpg_url con formato postgresql://).
        """
        conn_string = settings.asyncpg_url
        logger.info("checkpointer: abriendo conexión psycopg3")
        # W0135 false positive: asynccontextmanager unwinds inner async-with on generator close.
        # pylint: disable=contextmanager-generator-missing-cleanup
        async with AsyncPostgresSaver.from_conn_string(conn_string) as saver:
            await saver.setup()
            logger.info("checkpointer: tablas de checkpoints listas (setup completado)")
            yield saver
        logger.info("checkpointer: conexión psycopg3 cerrada")
