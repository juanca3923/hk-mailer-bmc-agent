# Memoria del agente

Resumen de cómo AgentForge **persiste y recupera** el contexto conversacional y la trazabilidad. El detalle de componentes y rutas está en [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).

## Continuidad del chat (lo que “recuerda” el LLM en un hilo)

- **Checkpointer de LangGraph** (`AsyncPostgresSaver` sobre Postgres): guarda el estado del grafo por **`thread_id`**, que en este proyecto equivale al **`chat_id`**. Así cada turno puede rehidratar el historial de mensajes del modelo sin que el cliente reenvíe todo el historial manualmente.
- Cada invocación pasa el **mensaje nuevo del usuario** y el checkpointer aporta el resto del hilo. Las skills locales dependen de la rama: en **`agent-base`**, catálogo en el system prompt y tool `skill_get_guide`; en **`deep-agent-base`**, descubrimiento vía Deep Agents ([`docs/skills-implementation.md`](skills-implementation.md)).

## Base de datos (auditoría y consultas)

- **`chats` / `chat_messages`**: registro de lo que dijo el usuario y el asistente para **trazabilidad**, análisis y posible entrenamiento futuro.
- **`agent_runs` / `agent_events`**: ejecución del turno, tiempos, tokens y eventos de herramientas.
- **`AgentPostgresStore`** (tabla `agent_memory_facts`): memoria **entre hilos** (hechos o preferencias) cuando el agente las persiste vía el store de LangGraph.

## Buscar en el pasado (tools `memory_*`)

El modelo puede **consultar** conversaciones y runs anteriores con las tools internas, por ejemplo:

- `memory_search_chats`, `memory_get_chat_messages` — historial por palabras clave o por `chat_id`.
- `memory_list_recent_runs`, `memory_get_run_events` — actividad reciente y traza de una run.

No sustituyen al checkpointer del hilo actual: sirven cuando el usuario pregunta por algo que ocurrió **en otro momento** o en otro chat.

Las consultas SQL de esas tools pasan por `AgentRunsService`; la serialización de filas usa `commons.serializers.MemorySerializer`.

## Errores en tools (grafo no se corta)

Si una tool falla (MCP, memoria, A2A, etc.), el grafo **no debe** dejar un `tool_use` sin `tool_result`: las excepciones de tool heredan `ToolAgentError` (`ToolException` + `AgentError`), y `configure_tool_error_handling` activa `handle_tool_error` para que LangChain ponga `str(exc)` en el `ToolMessage`. Chats con checkpoint inconsistente por fallos antiguos requieren un **chat nuevo** o limpiar el `thread_id` en tablas `langgraph_checkpoint_*`.

## Dónde mirar en código

- Turno y persistencia de mensajes: `src/commons/runner.py`.
- Checkpointer: `src/database/checkpointer.py`.
- Tools de memoria: `src/agent/internal_tools/memory_tools.py`.
- Lecturas de runs: `src/services/agent_runs_service.py`.
- Serialización: `src/commons/serializers/memory_serializer.py`.
- Política de errores en tools: `src/agent/tool_error_policy.py`.
