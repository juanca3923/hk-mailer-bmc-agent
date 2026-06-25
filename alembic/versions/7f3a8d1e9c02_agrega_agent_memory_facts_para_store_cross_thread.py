"""agrega agent_memory_facts para store cross-thread de LangGraph

Revision ID: 7f3a8d1e9c02
Revises: 0a2cbe1d4a6a
Create Date: 2026-04-16 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7f3a8d1e9c02"
down_revision: Union[str, Sequence[str], None] = "0a2cbe1d4a6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea la tabla agent_memory_facts.

    Cada fila representa un hecho cross-thread persistido por AgentPostgresStore.
    La clave lógica es (namespace, key); el valor es un JSONB libre.
    """
    op.create_table(
        "agent_memory_facts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("namespace", sa.String(255), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column(
            "value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("namespace", "key", name="uq_agent_memory_facts_ns_key"),
    )
    op.create_index(
        "ix_agent_memory_facts_namespace",
        "agent_memory_facts",
        ["namespace"],
        unique=False,
    )


def downgrade() -> None:
    """Elimina la tabla agent_memory_facts."""
    op.drop_index("ix_agent_memory_facts_namespace", table_name="agent_memory_facts")
    op.drop_table("agent_memory_facts")
