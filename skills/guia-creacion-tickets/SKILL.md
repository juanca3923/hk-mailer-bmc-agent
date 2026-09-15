---
name: guia-creacion-tickets
description: Guía de proceso para decidir Work Order vs Incidente, mapear columnas de categorización a parámetros de las tools, traducir Prioridad y cumplir los guards de negocio antes de crear, cerrar o modificar tickets BMC. Léela antes de llamar cualquier tool bmc_create_*/bmc_close_*.
---

# Guía de proceso — creación y cierre de tickets BMC

Esta guía cubre el **procedimiento común** a todas las skills de dominio
(`categorias-<dominio>`, hoy `categorias-eventos` y `categorias-usuario`): cómo decidir
el tipo de ticket, cómo mapear cualquiera de esas tablas a parámetros de
`bmc_create_incident`/`bmc_create_work_order`, y los guards de negocio. **Las skills de
dominio solo aportan la tabla de datos** — no repiten este procedimiento, así que si vas
a crear un ticket para un dominio conocido necesitas leer esta guía además de esa skill.

No existe ningún catálogo genérico de categorías: un caso que no encaje en ningún
dominio conocido usa el catch-all fijo de la sección 1, documentado **aquí** (no en
código ni variables de entorno) — así la mesa de servicio lo actualiza editando este
archivo, sin necesidad de reconstruir ni reiniciar el agente.

## 1. Cuándo es Work Order vs Incidente

**Primero, busca dominio**: revisa si hay un catálogo `categorias-<dominio>` con una
fila que aplique al caso — su columna `Tipo Servicio` decide el tipo.

- **Si aplica un dominio conocido**: la columna `Tipo Servicio` de la fila elegida
  decide — `Incidente` (algo que dejó de funcionar o se degradó sin planearlo; Impact/
  Urgency quedan fijos en `1-Extensive/Widespread`/`1-Critical`, no son parámetros de
  `bmc_create_incident`) o `Requerimiento` (una solicitud o trabajo planeado; tiene
  `priority` como parámetro libre, tomado de la fila).
- **Si NO aplica ningún dominio conocido**: el caso se crea **siempre como Work
  Order**, nunca como Incidente — sin importar si "suena" a algo roto o caído. Llama
  `bmc_create_work_order` pasando **exactamente** estos valores (catch-all confirmado
  por la mesa de servicio el 2026-09-14, para que lo triage manualmente — no los
  cambies ni los completes con otra cosa):

  | Parámetro | Valor |
  |---|---|
  | `categorization_tier_1` | `Gestion de tickets` |
  | `categorization_tier_2` | `Acompañamiento` |
  | `product_cat_tier_1` | `Gestion de casos` |
  | `product_cat_tier_2` | `Control` |
  | `product_cat_tier_3` | `Casos` |

  No existe un catch-all de Incidente — no se crean incidentes fuera de un dominio
  conocido. Si la mesa de servicio cambia esta combinación, solo hace falta editar
  esta tabla — no requiere ningún cambio de código ni redeploy del agente.

## 2. Mapeo columna → parámetro (aplica a cualquier skill de categorías)

Toda skill de categorías usa columnas equivalentes a estos conceptos, aunque el nombre
literal de la columna varíe entre fuentes (ej. "Cat Op 1" y "Categoria Operacional 1"
son la misma cosa). Copia siempre los valores de una **única fila**, sin mezclar la
categoría operacional de una fila con la de producto de otra.

| Concepto | `bmc_create_work_order` | `bmc_create_incident` |
|---|---|---|
| Categoría operacional 1 | `categorization_tier_1` | `categorization_tier_1` |
| Categoría operacional 2 | `categorization_tier_2` | `categorization_tier_2` |
| Categoría operacional 3 | *(sin parámetro — ignora esta columna si la fuente la trae)* | *(sin parámetro — ignora esta columna si la fuente la trae)* |
| Categoría de producto 1 | `product_cat_tier_1` | `product_categorization_tier_1` |
| Categoría de producto 2 | `product_cat_tier_2` | `product_categorization_tier_2` |
| Categoría de producto 3 | `product_cat_tier_3` | `product_categorization_tier_3` |
| Prioridad | `priority` (traducida ES→EN, ver tabla abajo) | *(sin parámetro — Impact/Urgency quedan fijos; ignora esta columna si la fuente la trae)* |
| Grupo asignado / Escalamiento | `assigned_group` | `assigned_group` |

### Mapeo Prioridad (ES) → `priority` (EN) — solo aplica a Work Order

| Prioridad (fuente) | Valor para `priority` |
|---------------------|----------------------|
| CRITICA / CRITICO | `Critical` |
| ALTA | `High` |
| MEDIA | `Medium` |
| BAJA | `Low` |

### Columnas informativas de catálogos de dominio

Un catálogo de dominio (`categorias-<dominio>`) puede traer columnas que no mapean a
ningún parámetro, solo dan contexto operativo — ej. `¿Susceptible de cierre en mesa?`
indica que la mesa suele resolver y cerrar ese caso en el mismo turno de atención.
**Nunca implican una regla automática**: no cierres ni cambies de comportamiento solo
por esa columna — sigue el protocolo normal de creación/cierre de `system.promt.md` en
todos los casos.

## 3. Si el caso encaja en un dominio pero ninguna fila describe el caso exacto

Cada skill de dominio (`categorias-<dominio>`) indica si su tabla es el catálogo
completo de ese dominio o solo una parte. Si el caso claramente pertenece a ese
dominio (p. ej. es un tema de usuario/red) pero ninguna fila lo describe con
precisión:

1. No inventes una combinación de categorías que no hayas visto en esa tabla.
2. Usa la fila más general y razonable de esa misma tabla, dejando claro que fue una
   elección aproximada.
3. Si el caso es ambiguo o crítico, prefiere preguntar antes de crear el ticket en vez
   de adivinar.

## 4. Campos obligatorios vs. fijados por el entorno

No pidas estos datos al usuario ni intentes pasarlos como parámetro — están fijados
por configuración del agente, no por el catálogo de categorías:

- Company, y nombre/apellido del **cliente** (`Customer First/Last Name`, solo Work
  Order — es una identidad fija distinta del solicitante).
- Impact y Urgency (solo Incidente, siempre fijos).

La categorización (operacional 1/2, producto 2-3 niveles, `priority`/`assigned_group`
cuando el tool los reciba como parámetro) es siempre obligatoria y nunca se inventa:
cuando aplica un dominio conocido sale de esa tabla según el mapeo de la sección 2;
cuando NO aplica ningún dominio, `bmc_create_work_order` la recibe igual, pero con los
valores catch-all exactos de la sección 1 (no hay default en código ni en variables de
entorno — están fijados aquí para que la mesa de servicio los edite sin redeploy).
`bmc_create_incident` no tiene catch-all — solo se llama cuando un dominio conocido
determinó Tipo Servicio = Incidente.

**`reporter_email` es obligatorio y NO sale del catálogo de categorías ni está
fijado**: es el correo de quien reporta el incidente o solicita el Work Order (pídelo
al usuario en modo interactivo, o tómalo del mensaje entrante en modo A2A). El nombre
y apellido del **solicitante** (`First Name`/`Last Name`, distinto del cliente) ya no
es un valor fijo — la tool lo resuelve buscando ese correo en `CTM:People`, y la
creación falla sin crear ningún ticket si no encuentra a esa persona registrada en
BMC. Ver `docs/CHANGELOG.md` para el detalle de esta resolución de identidad.

## 5. Guards de negocio que pueden rechazar la operación

- **Ticket cerrado**: ningún ticket con `Status = Closed` admite notas, adjuntos,
  cambios de estado ni un segundo cierre. Si el usuario pide modificar un ticket
  cerrado, infórmalo y no reintentes la operación.
- **Cierre solo por el propietario del servicio**: `bmc_close_work_order` y
  `bmc_close_incident` solo funcionan sobre un ticket cuyo `Submitter` sea el usuario
  de servicio de este agente. Si el ticket fue abierto por otra persona o sistema, el
  cierre fallará con un mensaje explícito — agregar notas o adjuntos a ese mismo ticket
  sigue estando permitido, solo el cierre está restringido.
- **Cierre de Work Order es de 3 pasos internos** (toma de propiedad → Completed →
  Closed) y **el de Incidente de 2 pasos** (toma de propiedad → Resolved), aunque para
  ti sea una sola llamada a la tool. Si la operación falla a mitad de camino, el ticket
  puede quedar en un estado intermedio (`In Progress`/`Completed`); no asumas que quedó
  cerrado — recomienda reintentar el cierre o escalar a un humano.
- **`description` de incidente tiene un límite duro de 100 caracteres** (`bmc_create_incident`
  y `bmc_close_incident`) — es el mismo campo AR en ambos casos, BMC rechaza toda la
  petición si te pasas, no la trunca. Redáctalo como un resumen corto; el detalle completo
  va en `detailed_decription` (creación) o en `resolution`/una nota aparte (cierre).

## 6. Calidad del asunto y la descripción

El `summary`/`description` (asunto) y el `detailed_description`/`detailed_decription`
(descripción detallada) de un ticket **no son campos de relleno**: la mesa y el
solicitante dependen de ellos para entender el caso sin volver a preguntar. Redáctalos
siempre a partir del mensaje real del usuario, nunca con una etiqueta genérica.

- **Asunto**: breve y específico — qué se afectó o qué se solicita, y para quién o qué
  sistema. Evita frases genéricas como "Solicitud de usuario" o "No funciona el
  sistema"; usa algo como "Alta de usuario de red — Juan Pérez, sede Bogotá" o
  "Aplicación de nómina caída para todos los usuarios de la sede Medellín". En
  incidente, `description` tiene además un límite duro de 100 caracteres (sección 5).
- **Descripción detallada**: incluye quién reporta o solicita, cuándo empezó (para
  incidentes) o para cuándo se necesita (para Work Orders), el síntoma o
  requerimiento exacto, el sistema/aplicación involucrado, y el alcance (cuántos
  usuarios o qué sede). Debe bastar para que la mesa actúe o diagnostique sin
  contactar de nuevo al usuario.
- Nunca copies el asunto como descripción ni dejes la descripción sin contenido real
  (ej. "Ver asunto"): son dos campos con propósito distinto.

## 7. Modo automatizado (A2A)

Los guards de arriba aplican igual cuando el mensaje viene de otro agente
orquestador. Si `bmc_close_work_order`/`bmc_close_incident` devuelve `success: false`
por un guard, refleja ese fallo en el resumen estructurado que devuelves — no lo
silencies ni reportes el ticket como cerrado si no lo está.

## 8. Checklist final antes de llamar `bmc_create_work_order`/`bmc_create_incident`

1. ¿Es Work Order o Incidente? Si aplicó una skill de dominio, usa su columna
   `Tipo Servicio`; si NO aplicó ningún dominio, es **siempre Work Order** (sección 1)
   — nunca crees un Incidente sin dominio conocido.
2. Si aplicó dominio: ¿leíste esa skill y elegiste una única fila completa, mapeada
   según la sección 2, sin inventar? Si NO aplicó dominio: ¿pasaste
   `categorization_tier_1/2`/`product_cat_tier_1/2/3` con los valores catch-all
   exactos de la sección 1, sin inventar otra combinación?
3. ¿Los campos obligatorios (descripción, y categorización/priority/assigned_group
   cuando aplicó dominio) están completos con valores reales, no inventados?
4. ¿El asunto y la descripción detallada son específicos y están redactados a partir
   del caso real (sección 6), no una etiqueta genérica?
5. Si es incidente, ¿el `description` (asunto) cabe en 100 caracteres? Si el caso
   necesita más detalle, va en `detailed_decription`, no ahí (sección 5).
6. ¿Tienes el correo real de quien reporta/solicita (`reporter_email`), sin inventarlo
   ni usar el tuyo propio?
7. ¿Evitaste pasar campos fijados por el entorno (company, identidad del cliente,
   impact/urgency)?
8. Si aplicó dominio pero ninguna fila describía el caso exacto (sección 3), ¿dejaste
   eso explícito en vez de simular certeza, en lugar de inventar una fila?
