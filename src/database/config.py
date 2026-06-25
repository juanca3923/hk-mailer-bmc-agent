"""Configuración de base de datos para el motor SQLAlchemy y Alembic."""

from __future__ import annotations

from functools import lru_cache

from config import Settings


@lru_cache(maxsize=1)
def _load_settings() -> Settings:
    """Carga y cachea la configuración del proyecto (singleton de módulo)."""
    return Settings.load()


class DatabaseConfig:
    """Provee URLs y flags de configuración de la base de datos.

    Centraliza la derivación de URLs (asyncpg para SQLAlchemy, psycopg para Alembic)
    para que el resto del proyecto no repita la lógica de transformación.
    """

    @staticmethod
    def url() -> str:
        """URL de conexión async para SQLAlchemy (postgresql+asyncpg://)."""
        return _load_settings().database_url

    @staticmethod
    def url_sync() -> str:
        """URL de conexión síncrona para Alembic (postgresql+psycopg://).

        Alembic usa un motor síncrono; se sustituye el driver asyncpg por psycopg v3.
        """
        url = DatabaseConfig.url()
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        return url

    @staticmethod
    def echo() -> bool:
        """Retorna True si el echo SQL está habilitado (para debug en desarrollo)."""
        return bool(_load_settings().db_echo)
