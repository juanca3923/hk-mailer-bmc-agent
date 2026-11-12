"""Servicio HTTP de AgentForge (FastAPI)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bmc.libs.preflight import run_startup_preflight
from commons.agent_http import start_agent, stop_agent
from config import Settings
from database.engine import close_engine, ensure_schema
from http_api.a2a import router as a2a_router
from http_api.routers.people_routes import router as people_router
from http_api.routers.rest_routes import router as rest_router

_http_settings = Settings.load()


@asynccontextmanager
async def lifespan(fast_app: FastAPI) -> AsyncIterator[None]:
    """Ciclo de vida: arranca el agente al subir y lo cierra al bajar."""
    fast_app.state.chat_tasks = set()  # set[asyncio.Task[object]]
    async with AsyncExitStack() as stack:
        await ensure_schema()
        await start_agent(fast_app, stack)
        await run_startup_preflight()
        try:
            yield
        finally:
            await stop_agent(fast_app)
            await close_engine()


app = FastAPI(
    title="AgentForge API",
    description="API HTTP para consultar estado, iniciar/parar el agente y enviar mensajes.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_http_settings.normalized_cors_origins(),
    allow_credentials=_http_settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(a2a_router)
app.include_router(rest_router)
app.include_router(people_router)


def run() -> None:
    """Punto de entrada para ejecutar el servidor con uvicorn."""
    settings = Settings.load()
    uvicorn.run(
        "http_api.app:app",
        host=settings.http_host,
        port=settings.http_port,
        reload=False,
    )
