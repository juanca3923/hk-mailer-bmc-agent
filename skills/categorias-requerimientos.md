---
name: categorias-requerimientos
description: Catálogo de categorías BMC Helix ARUS para crear Work Orders (Requerimientos). Consulta siempre antes de llamar bmc_create_work_order.
---

# Categorías BMC Helix — Requerimiento (Work Order)

Usa esta guía para seleccionar la combinación **exacta** de campos de categorización
al crear un **Work Order** con `bmc_create_work_order`.

## Campos que debes completar

| Parámetro en `bmc_create_work_order` | Columna en esta guía |
|---------------------------------|---------------------|
| `categorization_tier_1` | Cat Op 1 |
| `categorization_tier_2` | Cat Op 2 |
| `product_cat_tier_1` | Cat Prod 1 |
| `product_cat_tier_2` | Cat Prod 2 |
| `product_cat_tier_3` | Cat Prod 3 |
| `priority` | valor de la columna Priority (ya en inglés: `Medium`, `High`, `Low`, `Critical`) |
| `assigned_group` | Grupo (referencia) |

### Mapeo Prioridad (ES) → `priority` (EN)

| Prioridad | Valor para `priority` |
|-----------|----------------------|
| CRITICA | `Critical` |
| ALTA | `High` |
| MEDIA | `Medium` |
| BAJA | `Low` |

> **Regla:** elige la fila que mejor describe el caso del usuario.
> Copia los valores **exactamente** como aparecen en la tabla, todos de la misma fila
> (no mezcles Cat Op de una fila con Cat Prod de otra).

## Muestra de categorías (ambiente de pruebas arus-dev)

Esta tabla es una **muestra pequeña e ilustrativa**, no el catálogo completo. Sale de
`config/categorias_maya.json` en `bmc-mcp` (generado desde `CCTI_ARUS.xlsx`, el Excel
del **ambiente de pruebas**; el propio dato aclara que el emparejamiento categoría
operacional↔producto es mecánico y no representa una caracterización ITSM formal).
Cubre los escenarios más comunes de un área de TI: usuarios/telefonía, cambio de
contraseña, accesos/instalaciones y solicitudes generales. Si el caso del usuario no
encaja en ninguna fila, dilo explícitamente y pide confirmación en vez de inventar una
combinación — no la adivines.

| Cat Op 1 | Cat Op 2 | Cat Prod 1 | Cat Prod 2 | Cat Prod 3 | Priority | Grupo (referencia) |
|----------|----------|-----------|-----------|-----------|----------|---------------------|
| Aplicacion | Actualizar usuarios masivo | GTI | Plataforma | Herramientas ITSM | Medium | HERRAMIENTAS DE GESTION |
| Aplicacion | Crear / modificar / eliminar usuario en consola | Software | Iris | Aplicacion | Medium | APLICACIONES INTERNAS |
| Aplicacion | Contraseña incorrecta / bloqueada | Software | Efi activos | Aplicacion | Medium | APLICACIONES INTERNAS |
| Aplicacion | Crear / cambiar contraseña | Software | Efi dedicacion de horas y subrepartos | Aplicacion | Medium | APLICACIONES INTERNAS |
| Administracion de TI | Telefonia | Gestion de casos | Control | Casos | Medium | TELEFONIA |
| Comunicaciones | Permiso de navegacion usuario | TB Otros Servicios de Infraestructura | Canales de Comunicacion | Otra solicitud | Medium | TELEFONIA |
| Infraestructura | Crear / modificar / eliminar / suspender usuario | TB Servicio Navegacion Internet | Redes | Revision de switches | Medium | GTI.REDES |
| Aplicacion | Instalar aplicacion | TB Gestion de Servicios | General | Llamada equivocada/transferida | Medium | SOPORTE MESA DE SERVICIO |
| Aplicacion | Generar acceso | TB Estaciones de Trabajo | Portatil | Eliminar temporales y cookies | Medium | MOSAICO |
| Administrativos | Daño tarjeta de acceso | GTI | Backup | Plataforma | Medium | PUC.ADMINISTRATIVO MEDELLIN |

## Si el caso no está en la muestra

Esta guía **no reemplaza** el catálogo Maya completo (~1900 combinaciones en
`bmc-mcp/config/categorias_maya.json`). Si el requerimiento no encaja en ninguna fila
de arriba:

1. No inventes una combinación de categorías que no hayas visto en esta tabla.
2. Usa la categorización operacional/producto más general y razonable que sí conozcas,
   dejando claro en la nota o en tu respuesta al usuario que fue una elección
   aproximada.
3. Si el caso es ambiguo, prefiere preguntar antes de crear el ticket en vez de
   adivinar.

---
_Muestra generada desde `bmc-mcp/config/categorias_maya.json` (fuente: `CCTI_ARUS.xlsx`,
ambiente de pruebas) el 2026-07-29. Re-sincronizar cuando ese catálogo cambie de forma
relevante._
