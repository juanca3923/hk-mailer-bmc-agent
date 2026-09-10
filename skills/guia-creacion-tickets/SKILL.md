---
name: guia-creacion-tickets
description: Guía de proceso para decidir Work Order vs Incidente, mapear columnas de categorización a parámetros de las tools, traducir Prioridad y cumplir los guards de negocio antes de crear, cerrar o modificar tickets BMC. Léela antes de llamar cualquier tool bmc_create_*/bmc_close_*.
---

# Guía de proceso — creación y cierre de tickets BMC

Esta guía cubre el **procedimiento común** a todas las skills de categorías
(`categorias-incidentes`, `categorias-requerimientos`, y las de dominio
`categorias-<dominio>` como `categorias-usuario`): cómo decidir el tipo de ticket, cómo
mapear cualquiera de esas tablas a parámetros de `bmc_create_incident`/
`bmc_create_work_order`, y los guards de negocio. **Las skills de categorías solo
aportan la tabla de datos** — no repiten este procedimiento, así que si vas a crear un
ticket necesitas leer esta guía además de la skill de categorías que aplique.

## 1. Cuándo es Work Order vs Incidente

**Antes de aplicar el heurístico de esta sección**, revisa si hay un catálogo de
dominio (`categorias-<dominio>`) con una fila que aplique al caso: su columna
`Tipo Servicio` decide el tipo y tiene prioridad sobre lo que sigue. El heurístico de
abajo es el *fallback* para cuando no hay dominio conocido o ninguna fila encaja.

- **Incidente**: algo que ya funcionaba dejó de funcionar o se degradó sin planearlo
  (aplicación caída, usuario bloqueado, servicio inaccesible). Todo incidente creado
  por este agente queda con Impact/Urgency fijos en `1-Extensive/Widespread` /
  `1-Critical` — no son parámetros de `bmc_create_incident`, no los inventes ni los
  preguntes.
- **Work Order**: una solicitud o trabajo planeado (alta de usuario, cambio de
  configuración, instalación, acceso nuevo). No tiene Impact/Urgency; sí tiene
  `priority` como parámetro libre, tomado del catálogo de categorías.

Regla rápida: si el usuario reporta algo "roto", "caído" o "no funciona" → Incidente.
Si pide algo "nuevo", "programado" o "un cambio" → Work Order.

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

## 3. Si el caso no encaja en ninguna fila

Las tablas de `categorias-incidentes` y `categorias-requerimientos` son una **muestra
pequeña**, no el catálogo completo de BMC (~1900 combinaciones reales); las tablas de
dominio (`categorias-<dominio>`) sí pueden ser catálogos completos para ese dominio
específico — cada skill lo indica. Si el caso del usuario no encaja en ninguna fila (de
dominio ni genérica):

1. No inventes una combinación de categorías que no hayas visto en ninguna tabla.
2. Usa la categorización operacional/producto más general y razonable que sí conozcas,
   dejando claro que fue una elección aproximada.
3. Si el caso es ambiguo o crítico, prefiere preguntar antes de crear el ticket en vez
   de adivinar.

## 4. Campos obligatorios vs. fijados por el entorno

No pidas estos datos al usuario ni intentes pasarlos como parámetro — están fijados
por configuración del agente, no por el catálogo de categorías:

- Company, nombre/apellido del solicitante y del cliente (Work Order e Incidente).
- Impact y Urgency (solo Incidente, siempre fijos).

Sí son obligatorios y deben salir del catálogo de categorías, según el mapeo de la
sección 2: categoría operacional 1/2, categorización de producto (2-3 niveles), y
`priority`/`assigned_group` cuando el tool los reciba como parámetro.

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

## 6. Modo automatizado (A2A)

Los guards de arriba aplican igual cuando el mensaje viene de otro agente
orquestador. Si `bmc_close_work_order`/`bmc_close_incident` devuelve `success: false`
por un guard, refleja ese fallo en el resumen estructurado que devuelves — no lo
silencies ni reportes el ticket como cerrado si no lo está.

## 7. Checklist final antes de llamar `bmc_create_work_order`/`bmc_create_incident`

1. ¿Es Work Order o Incidente? Si aplicó una skill de dominio, usa su columna
   `Tipo Servicio`; si no, confirma con el heurístico de la sección 1.
2. ¿Leíste la skill de categorías correspondiente (genérica o de dominio) y elegiste
   una única fila completa, mapeada según la sección 2?
3. ¿Los campos obligatorios (descripción, categorización, y priority/assigned_group
   cuando aplique) están completos con valores reales, no inventados?
4. ¿Evitaste pasar campos fijados por el entorno (company, identidad, impact/urgency)?
5. Si el caso no encajaba en ninguna fila del catálogo, ¿dejaste eso explícito en vez
   de simular certeza?
