"""Store persistente en Postgres para memoria cross-thread de LangGraph."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from langgraph.store.base import (
    BaseStore,
    GetOp,
    Item,
    ListNamespacesOp,
    MatchCondition,
    PutOp,
    Result,
    SearchItem,
    SearchOp,
)
from sqlalchemy import delete, select, text, update

from config import get_logger
from constants.database import NS_SEP
from database.engine import get_session
from database.models import AgentMemoryFact

logger = get_logger()


def _ns_to_str(namespace: tuple[str, ...]) -> str:
    """Serializa un namespace tuple a string para almacenar en BD."""
    return NS_SEP.join(namespace)


def _str_to_ns(value: str) -> tuple[str, ...]:
    """Deserializa un namespace string a tuple."""
    return tuple(value.split(NS_SEP)) if value else ()


class AgentPostgresStore(BaseStore):
    """Store persistente en Postgres para memoria cross-thread de LangGraph.

    Implementa la API BaseStore de LangGraph usando la tabla `agent_memory_facts`
    gestionada por SQLAlchemy. Las operaciones async (abatch) son las reales;
    las síncronas (batch) delegan en un event loop auxiliar y solo deben usarse
    fuera de contextos async (p. ej. scripts de diagnóstico).

    Operaciones soportadas: GetOp, PutOp (incluye delete con value=None),
    SearchOp (búsqueda ILIKE en value::text), ListNamespacesOp.
    """

    # ------------------------------------------------------------------
    # API principal: batch y abatch
    # ------------------------------------------------------------------

    def batch(self, ops: object) -> list[Result]:
        """Ejecuta operaciones síncronamente. Solo para uso fuera de contextos async."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        return loop.run_until_complete(self.abatch(ops))  # type: ignore[arg-type]

    async def abatch(self, ops: list[object]) -> list[Result]:  # type: ignore[override]
        """Ejecuta las operaciones en batch de forma asíncrona."""
        results: list[Result] = []
        for op in ops:
            if isinstance(op, GetOp):
                results.append(await self._aget(op))
            elif isinstance(op, PutOp):
                await self._aput(op)
                results.append(None)
            elif isinstance(op, SearchOp):
                results.append(await self._asearch(op))
            elif isinstance(op, ListNamespacesOp):
                results.append(await self._alist_namespaces(op))
            else:
                results.append(None)
        return results

    # ------------------------------------------------------------------
    # Implementaciones internas de cada operación
    # ------------------------------------------------------------------

    async def _aget(self, op: GetOp) -> Item | None:
        """Recupera un ítem por namespace + key."""
        ns = _ns_to_str(op.namespace)
        async with get_session() as session:
            row = (
                await session.execute(
                    select(AgentMemoryFact).where(
                        AgentMemoryFact.namespace == ns,
                        AgentMemoryFact.key == op.key,
                    )
                )
            ).scalar_one_or_none()

        if row is None:
            logger.debug("store.aget: namespace=%r key=%r → not found", ns, op.key)
            return None

        logger.debug("store.aget: namespace=%r key=%r → found", ns, op.key)
        return Item(
            value=dict(row.value),
            key=row.key,
            namespace=_str_to_ns(row.namespace),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _aput(self, op: PutOp) -> None:
        """Upsert o delete de un ítem según op.value."""
        ns = _ns_to_str(op.namespace)

        if op.value is None:
            # value=None → borrar
            async with get_session() as session:
                await session.execute(
                    delete(AgentMemoryFact).where(
                        AgentMemoryFact.namespace == ns,
                        AgentMemoryFact.key == op.key,
                    )
                )
                await session.commit()
            logger.debug("store.aput: delete namespace=%r key=%r", ns, op.key)
            return

        now = datetime.now(timezone.utc)
        async with get_session() as session:
            existing = (
                await session.execute(
                    select(AgentMemoryFact).where(
                        AgentMemoryFact.namespace == ns,
                        AgentMemoryFact.key == op.key,
                    )
                )
            ).scalar_one_or_none()

            if existing is not None:
                await session.execute(
                    update(AgentMemoryFact)
                    .where(
                        AgentMemoryFact.namespace == ns,
                        AgentMemoryFact.key == op.key,
                    )
                    .values(value=op.value, updated_at=now)
                )
            else:
                session.add(
                    AgentMemoryFact(
                        id=uuid4(),
                        namespace=ns,
                        key=op.key,
                        value=op.value,
                        created_at=now,
                        updated_at=now,
                    )
                )
            await session.commit()
        logger.debug(
            "store.aput: upsert namespace=%r key=%r value_keys=%s",
            ns,
            op.key,
            list(op.value),
        )

    async def _asearch(self, op: SearchOp) -> list[SearchItem]:
        """Búsqueda ILIKE en value::text dentro de un prefijo de namespace."""
        ns_prefix = _ns_to_str(op.namespace_prefix)
        async with get_session() as session:
            stmt = select(AgentMemoryFact).where(AgentMemoryFact.namespace.like(f"{ns_prefix}%"))
            if op.query:
                stmt = stmt.where(text("value::text ILIKE :q").bindparams(q=f"%{op.query}%"))
            stmt = stmt.offset(op.offset).limit(op.limit)
            rows = list((await session.execute(stmt)).scalars().all())

        logger.debug(
            "store.asearch: ns_prefix=%r query_len=%d limit=%d → %d resultados",
            ns_prefix,
            len(op.query or ""),
            op.limit,
            len(rows),
        )
        return [
            SearchItem(
                value=dict(row.value),
                key=row.key,
                namespace=_str_to_ns(row.namespace),
                created_at=row.created_at,
                updated_at=row.updated_at,
                score=None,
            )
            for row in rows
        ]

    async def _alist_namespaces(self, op: ListNamespacesOp) -> list[tuple[str, ...]]:
        """Lista los namespaces almacenados que coinciden con las condiciones."""
        async with get_session() as session:
            rows = list((await session.execute(select(AgentMemoryFact.namespace).distinct())).scalars().all())

        namespaces = [_str_to_ns(ns) for ns in rows]

        if op.match_conditions:
            namespaces = [ns for ns in namespaces if self._matches(ns, op.match_conditions)]

        if op.max_depth is not None:
            namespaces = [ns[: op.max_depth] for ns in namespaces]
            # Eliminar duplicados que resulten del truncado
            seen: set[tuple[str, ...]] = set()
            unique: list[tuple[str, ...]] = []
            for ns in namespaces:
                if ns not in seen:
                    seen.add(ns)
                    unique.append(ns)
            namespaces = unique

        result = namespaces[op.offset : op.offset + op.limit]
        logger.debug("store.alist_namespaces: total=%d retornados=%d", len(namespaces), len(result))
        return result

    def _matches(self, namespace: tuple[str, ...], conditions: tuple[MatchCondition, ...]) -> bool:
        """Evalúa condiciones de prefijo/sufijo sobre un namespace."""
        for cond in conditions:
            if cond.match_type == "prefix" and namespace[: len(cond.path)] != cond.path:
                return False
            if cond.match_type == "suffix" and namespace[-len(cond.path) :] != cond.path:
                return False
        return True
