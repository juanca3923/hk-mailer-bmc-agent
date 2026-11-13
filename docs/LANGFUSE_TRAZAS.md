# Trazas en Langfuse: cómo leerlas

Cada turno del agente (un mensaje de chat o una llamada A2A) es **un trace** en Langfuse. Se instrumenta con el `CallbackHandler` de LangChain (los pasos internos: nodos, LLM, tools) y `propagate_attributes` alrededor de la invocación del grafo (`agent/observability/langfuse_tracing.py`), que le da al trace su nombre, sesión, tags y metadata. El callback propio que guarda eventos en Postgres (`AgentRunCallbackHandler`) es independiente.

## Qué lleva cada trace
| Atributo | Valor |
|---|---|
| Nombre | `<AGENT_SLUG>:<modo>` — modo `chat` o `a2a` |
| Sesión (`session_id`) | el `chat_id` del turno (el mismo `thread_id` del checkpointer); un chat = una sesión. Si otro agente nos llamó por A2A y mandó su `caller_chat_id`, ese pasa a ser la sesión |
| Tags | `<AGENT_SLUG>` y el modo |
| Metadata | `agent_run_id`, `own_chat_id` y, si hubo llamante, `caller_agent`, `caller_chat_id`, `caller_run_id` |

Todos son ASCII de hasta 200 caracteres; nunca se envían correos, asuntos ni texto de mensajes. Sin credenciales de Langfuse no se hace nada.

## Dónde mirar
- **Traces**: una fila por run. Filtra por *Name* o *Tags* (`chat`, `a2a`). Al abrir uno ves el árbol completo del turno.
- **Sessions**: un chat con todos sus turnos, y — con A2A — los traces del agente BMC que atendió ese chat del mailer.
- **Observations**: lista *todos los spans* sueltos (cada nodo, LLM y tool de cada run). Es normal que sean muchos más que los traces; úsala solo para buscar un span concreto.

## Unión mailer ↔ BMC
El mailer envía en `message.metadata` del mensaje A2A `caller_agent`, `caller_chat_id` y `caller_run_id`. Aquí (`http_api/a2a_jsonrpc.py`) solo se aceptan esas tres claves, como texto de hasta 64 caracteres; cualquier otra cosa se ignora sin fallar el mensaje. Si llega `caller_chat_id`, es la sesión del trace del BMC, así que el chat del mailer muestra los traces de los dos agentes; cada uno conserva sus propios traces y su propio chat. Sin llamante (chat directo o A2A sin metadata) la sesión es el `chat_id` del BMC.

## Costos
Los **tokens** siempre se acumulan, pero el **costo** (`$`) solo aparece si, al ingestar la observación, existe una definición de modelo con precios cuyo patrón coincide con el nombre del modelo. Langfuse trae precios de OpenAI, Anthropic y Google; no de modelos como `meta-llama/Llama-3.3-70B-Instruct` (servido por Hugging Face), por eso se ven tokens con `$0.00`.

**Cómo habilitarlo** (Project Settings > Models > *Add model definition*):
- *Match pattern*: `(?i)^meta-llama/Llama-3\.3-70B-Instruct$` (el nombre exacto que muestra la observación).
- Precios de entrada (`input`) y salida (`output`) según el proveedor; confirma en pantalla si la unidad es por token o por millón. También por API: `POST /api/public/models` con `modelName`, `matchPattern`, `unit: "TOKENS"`, `inputPrice` y `outputPrice`.

**Límites**: la definición **no es retroactiva**; lo ya ingestado queda en `$0`. El gasto anterior se estima a mano: `tokens_entrada × precio_entrada + tokens_salida × precio_salida`. Desde que se crea, los dashboards *Model costs* acumulan el gasto.
