---
name: categorias-usuario
description: Catálogo de categorización BMC Helix ARUS del dominio "usuario de red". Cubre Incidente y Work Order — la columna Tipo Servicio de cada fila decide cuál. Consúltalo antes que las skills genéricas cuando el caso encaje en este dominio.
---

# Categorías BMC Helix — dominio "usuario de red"

Tabla de datos para el dominio **usuario de red** (altas/bajas de usuario,
contraseñas, estado de casos). A diferencia de `categorias-incidentes`/
`categorias-requerimientos` (separadas por tipo), esta tabla mezcla ambos: la columna
**`Tipo Servicio`** de la fila decide si es Incidente o Work Order, con prioridad sobre
el heurístico genérico (`guia-creacion-tickets`, sección 1). El mapeo columna →
parámetro, la traducción de Prioridad y el significado de
`¿Susceptible de cierre en mesa?` están en `guia-creacion-tickets` (sección 2) — no se
repiten aquí.

Catálogo completo entregado por la mesa de servicio (no una muestra Maya):

| Tipo Servicio | Categoria Operacional 1 | Categoria Operacional 2 | Categoria Operacional 3 | Categoria de Producto 1 | Categoria de Producto 2 | Categoria de Producto 3 | Prioridad | ¿Susceptible de cierre en mesa? | Escalamiento 1 |
|---|---|---|---|---|---|---|---|---|---|
| Requerimiento | Aplicacion | Crear/cambiar contraseña | | Software | Gestiona tu acceso | Aplicacion | ALTA | SI | SOPORTE MESA DE SERVICIO |
| Requerimiento | Aplicacion | Crear/modificar/eliminar/activar/inactivar/desbloquear usuario | | Software | Gestiona tu acceso | Aplicacion | ALTA | SI | SOPORTE MESA DE SERVICIO |
| Requerimiento | Gestion de tickets | Informacion estado del caso | | Gestion de casos | Control | Casos | CRITICO | SI | SOPORTE MESA DE SERVICIO |

Hoy las 3 filas dan `Requerimiento`; este catálogo puede sumar filas `Incidente` más
adelante sin cambiar esta skill. Si el caso no encaja en ninguna fila, ver
`guia-creacion-tickets` sección 3.

---
_Catálogo del dominio "usuario de red" entregado por la mesa de servicio el
2026-09-01. Re-sincronizar cuando ese catálogo cambie._
