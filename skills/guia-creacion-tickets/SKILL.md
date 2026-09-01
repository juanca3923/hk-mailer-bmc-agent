---
name: guia-creacion-tickets
description: Guía de proceso para decidir Work Order vs Incidente, completar la categorización y cumplir los guards de negocio antes de crear, cerrar o modificar tickets BMC. Léela antes de llamar cualquier tool bmc_create_*/bmc_close_*.
---

# Guía de proceso — creación y cierre de tickets BMC

Esta guía cubre el **procedimiento**, no el catálogo de categorías en sí. Para elegir
los valores exactos de categorización usa `skill_get_guide("categorias-incidentes")` o
`skill_get_guide("categorias-requerimientos")` según corresponda. Pero **revisa primero**
si existe una skill de dominio más específica (stem `categorias-<dominio>`, p. ej.
`categorias-usuario` para casos de usuario/red): esas tablas pueden cubrir tanto
Incidente como Work Order — su columna `Tipo Servicio` decide el tipo y tiene
prioridad sobre el heurístico de la sección 1 — ver la regla de selección de dominio en
`system.promt.md`.

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

## 2. Categorización: una única fila, sin mezclar

Todos los campos de categorización (`categorization_tier_1/2`,
`product_cat_tier_*`/`product_categorization_tier_*`, y `priority`/`assigned_group`
cuando aplique) deben salir de la **misma fila** de la tabla en `categorias-incidentes`,
`categorias-requerimientos`, o la skill de dominio que aplicó (`categorias-<dominio>`).
Nunca combines la categoría operacional de una fila con la categoría de producto de
otra, aunque ambas existan en la tabla — la combinación completa es lo que importa, no
cada campo por separado.

Las tablas de esas dos skills son una **muestra pequeña**, no el catálogo completo de
BMC. Si el caso del usuario no encaja en ninguna fila, no inventes una combinación:
usa la categorización más general y razonable que sí conozcas, o pregunta antes de
crear el ticket si el caso es ambiguo o crítico.

## 3. Campos obligatorios vs. fijados por el entorno

No pidas estos datos al usuario ni intentes pasarlos como parámetro — están fijados
por configuración del agente, no por el catálogo de categorías:

- Company, nombre/apellido del solicitante y del cliente (Work Order e Incidente).
- Impact y Urgency (solo Incidente, siempre fijos).

Sí son obligatorios y deben salir del catálogo de categorías: `categorization_tier_1/2`,
categorización de producto (2-3 niveles), y `priority`/`assigned_group` cuando el tool
los reciba como parámetro.

## 4. Guards de negocio que pueden rechazar la operación

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

## 5. Modo automatizado (A2A)

Los guards de arriba aplican igual quando el mensaje viene de otro agente
orquestador. Si `bmc_close_work_order`/`bmc_close_incident` devuelve `success: false`
por un guard, refleja ese fallo en el resumen estructurado que devuelves — no lo
silencies ni reportes el ticket como cerrado si no lo está.

## 6. Checklist final antes de llamar `bmc_create_work_order`/`bmc_create_incident`

1. ¿Es Work Order o Incidente? Si aplicó una skill de dominio, usa su columna
   `Tipo Servicio`; si no, confirma con el heurístico de la sección 1.
2. ¿Leíste la skill de categorías correspondiente y elegiste una única fila completa?
3. ¿Los campos obligatorios (descripción, categorización, y priority/assigned_group
   cuando aplique) están completos con valores reales, no inventados?
4. ¿Evitaste pasar campos fijados por el entorno (company, identidad, impact/urgency)?
5. Si el caso no encajaba en ninguna fila del catálogo, ¿dejaste eso explícito en vez
   de simular certeza?
