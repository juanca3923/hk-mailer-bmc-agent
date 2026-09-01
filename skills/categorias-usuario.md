---
name: categorias-usuario
description: Catálogo de categorización BMC Helix ARUS del dominio "usuario de red". Cubre Incidente y Work Order — la columna Tipo Servicio de cada fila decide cuál. Consúltalo antes que las skills genéricas cuando el caso encaje en este dominio.
---

# Categorías BMC Helix — dominio "usuario de red"

Usa esta guía cuando el caso encaje en el dominio **usuario de red** (altas/bajas de
usuario, contraseñas, estado de casos, etc.). A diferencia de las skills genéricas
(`categorias-incidentes`, `categorias-requerimientos`, separadas por tipo de ticket),
esta tabla mezcla ambos tipos: **la columna `Tipo Servicio` de la fila que aplique
decide si el ticket es Incidente o Work Order**.

**Esta decisión tiene prioridad sobre el heurístico genérico** ("roto/caído" →
Incidente, "planeado/nuevo" → Work Order) de `guia-creacion-tickets`: si una fila de
esta tabla describe el caso, usa su `Tipo Servicio` tal cual, aunque el caso "suene"
distinto a lo que diría el heurístico genérico.

## Campos que debes completar

Los primeros dos parámetros (`categorization_tier_1`, `categorization_tier_2`) tienen
el mismo nombre en ambos tools; el resto cambia según el `Tipo Servicio` de la fila.

### Si `Tipo Servicio = Requerimiento` → `bmc_create_work_order`

| Parámetro | Columna en esta guía |
|---|---|
| `categorization_tier_1` | Categoria Operacional 1 |
| `categorization_tier_2` | Categoria Operacional 2 |
| `product_cat_tier_1` | Categoria de Producto 1 |
| `product_cat_tier_2` | Categoria de Producto 2 |
| `product_cat_tier_3` | Categoria de Producto 3 |
| `priority` | Prioridad, traducida ES→EN (ver tabla abajo) |
| `assigned_group` | Escalamiento 1 |

### Si `Tipo Servicio = Incidente` → `bmc_create_incident`

| Parámetro | Columna en esta guía |
|---|---|
| `categorization_tier_1` | Categoria Operacional 1 |
| `categorization_tier_2` | Categoria Operacional 2 |
| `product_categorization_tier_1` | Categoria de Producto 1 |
| `product_categorization_tier_2` | Categoria de Producto 2 |
| `product_categorization_tier_3` | Categoria de Producto 3 |
| `assigned_group` | Escalamiento 1 |

**La columna Prioridad no aplica a un Incidente**: `bmc_create_incident` no recibe
`priority` como parámetro — Impact y Urgency quedan fijos por el agente
(`1-Extensive/Widespread` / `1-Critical`). Si `Tipo Servicio = Incidente`, ignora el
valor de Prioridad de la fila.

**Categoria Operacional 3** de la fuente no tiene parámetro correspondiente en ninguno
de los dos tools hoy: en las filas de este dominio siempre viene vacía; no intentes
mapearla a ningún campo.

### Mapeo Prioridad (ES) → `priority` (EN) — solo aplica a Requerimiento

| Prioridad (fuente) | Valor para `priority` |
|---------------------|----------------------|
| CRITICO / CRITICA | `Critical` |
| ALTA | `High` |
| MEDIA | `Medium` |
| BAJA | `Low` |

> **Regla:** elige la fila que mejor describe el caso del usuario.
> Copia los valores **exactamente** como aparecen en la tabla, todos de la misma fila
> (no mezcles Categoria Operacional de una fila con Categoria de Producto de otra).

## Catálogo — dominio "usuario de red"

A diferencia de `categorias-incidentes` y `categorias-requerimientos` (muestras
extraídas de `categorias_maya.json`/`CCTI_ARUS.xlsx`, ambiente de pruebas), esta tabla
fue entregada directamente por la mesa de servicio como el **catálogo completo** para
este dominio — no es una muestra parcial de un catálogo mayor.

| Tipo Servicio | Categoria Operacional 1 | Categoria Operacional 2 | Categoria Operacional 3 | Categoria de Producto 1 | Categoria de Producto 2 | Categoria de Producto 3 | Prioridad | ¿Susceptible de cierre en mesa? | Escalamiento 1 |
|---|---|---|---|---|---|---|---|---|---|
| Requerimiento | Aplicacion | Crear/cambiar contraseña | | Software | Gestiona tu acceso | Aplicacion | ALTA | SI | SOPORTE MESA DE SERVICIO |
| Requerimiento | Aplicacion | Crear/modificar/eliminar/activar/inactivar/desbloquear usuario | | Software | Gestiona tu acceso | Aplicacion | ALTA | SI | SOPORTE MESA DE SERVICIO |
| Requerimiento | Gestion de tickets | Informacion estado del caso | | Gestion de casos | Control | Casos | CRITICO | SI | SOPORTE MESA DE SERVICIO |

Hoy las 3 filas dan `Requerimiento`. Este catálogo puede crecer con filas
`Incidente` más adelante — cuando eso pase, aplica la rama de `bmc_create_incident`
de arriba para esas filas.

### Sobre "¿Susceptible de cierre en mesa?"

Esta columna es **informativa**: indica que, en la operación real, la mesa de servicio
suele resolver y cerrar estos casos ella misma en el mismo turno de atención. **No
implica una regla automática en este agente** — no cierres el ticket solo porque la fila
diga `SI`. Sigue el protocolo normal ya definido en `system.promt.md`:
- En modo interactivo, confirma con el usuario antes de cerrar (`bmc_close_work_order`/
  `bmc_close_incident` son irreversibles).
- En modo automatizado A2A, aplica el ciclo completo (crear → nota → cerrar) que ya
  describe `system.promt.md` para ese modo, igual que para cualquier otro ticket.

## Si el caso no está en la tabla

Aunque este catálogo se presenta como completo para "usuario de red", puede llegar un
caso de ese dominio que no encaje en ninguna de las 3 filas:

1. No inventes una combinación de categorías que no hayas visto en esta tabla.
2. Considera si el caso en realidad pertenece a otro dominio o a la categorización
   genérica (`categorias-incidentes` / `categorias-requerimientos`) en vez de forzarlo
   aquí.
3. Si sigue siendo ambiguo, prefiere preguntar antes de crear el ticket en vez de
   adivinar.

---
_Catálogo del dominio "usuario de red" entregado por la mesa de servicio el
2026-09-01. Re-sincronizar cuando ese catálogo cambie._
