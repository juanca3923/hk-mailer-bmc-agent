---
name: categorias-incidentes
description: Catálogo de categorías BMC Helix ARUS para crear Incidentes. Consulta siempre antes de llamar bmc_create_incident.
---

# Categorías BMC Helix — Incidente

Usa esta guía para seleccionar la combinación **exacta** de campos de categorización
al crear un **incidente** con `bmc_create_incident`.

## Campos que debes completar

| Parámetro en `bmc_create_incident` | Columna en esta guía |
|-------------------------------|---------------------|
| `categorization_tier_1` | Cat Op 1 |
| `categorization_tier_2` | Cat Op 2 |
| `product_categorization_tier_1` | Cat Prod 1 |
| `product_categorization_tier_2` | Cat Prod 2 |
| `product_categorization_tier_3` | Cat Prod 3 |
| `assigned_group` | Grupo Asignado |

`impact` y `urgency` **ya no son parámetros** de `bmc_create_incident`: todo incidente
creado por este agente queda fijo en Impact `1-Extensive/Widespread` / Urgency
`1-Critical` (misma regla que aplica el servidor MCP hoy). No intentes pasarlos ni
preguntarle al usuario por ellos.

> **Regla:** elige la fila que mejor describe el caso del usuario.
> Copia los valores **exactamente** como aparecen en la tabla, todos de la misma fila
> (no mezcles Cat Op de una fila con Cat Prod de otra).
> `categorization_tier_1`/`categorization_tier_2` puede dejarse vacío `""` solo si
> ninguna fila de la tabla aplica al caso; en ese caso completa al menos la
> categorización de producto.

## Muestra de categorías (ambiente de pruebas arus-dev)

Esta tabla es una **muestra pequeña e ilustrativa**, no el catálogo completo. Sale de
`config/categorias_maya.json` en `bmc-mcp` (generado desde `CCTI_ARUS.xlsx`, el Excel
del **ambiente de pruebas**; el propio dato aclara que el emparejamiento categoría
operacional↔producto es mecánico y no representa una caracterización ITSM formal).
Cubre los escenarios más comunes de un área de TI: usuarios/telefonía, cambio de
contraseña, caída de aplicaciones y solicitudes generales. Si el caso del usuario no
encaja en ninguna fila, dilo explícitamente y pide confirmación en vez de inventar una
combinación — no la adivines.

| Cat Op 1 | Cat Op 2 | Cat Prod 1 | Cat Prod 2 | Cat Prod 3 | Prioridad | Grupo Asignado |
|----------|----------|-----------|-----------|-----------|-----------|----------------|
| Aplicacion | Aplicacion caida | GTI | Servidores | Linux | MEDIA | HERRAMIENTAS DE GESTION |
| Aplicacion | Caida aplicacion | Proceso de negocio | Gestion | Financiera | MEDIA | SOPORTE MESA DE SERVICIO |
| Aplicacion | Contraseña incorrecta / bloqueada | Software | Efi activos | Aplicacion | MEDIA | APLICACIONES INTERNAS |
| Aplicacion | Crear / cambiar contraseña | Software | Efi dedicacion de horas y subrepartos | Aplicacion | MEDIA | APLICACIONES INTERNAS |
| Aplicacion | Usuario bloqueado | TB Laserfiche | Facturacion Electronica | Acceso denegado | MEDIA | APLICACIONES INTERNAS |
| Administracion de TI | Telefonia | Gestion de casos | Control | Casos | MEDIA | TELEFONIA |
| Equipos Tecnologicos | Verificar datos del usuario | TB Servicio de Portal Web | Extranet Tebsa | Cambio de contraseña | MEDIA | SOPORTE EN SITIO MEDELLIN |
| NOC | Cambiar contraseña usuario | TB Software Complementario | Videoconferencias | Problemas de video | MEDIA | GTI.CONSOLA MONITOREO |
| Infraestructura | Crear / modificar / eliminar / suspender usuario | TB Servicio Navegacion Internet | Redes | Revision de switches | MEDIA | GTI.REDES |
| CONECTIVIDAD | Caida del servicio | TB Otros Servicios de Infraestructura | Servidores | Alto consumo de recursos | MEDIA | GTI.REDES |

## Si el caso no está en la muestra

Esta guía **no reemplaza** el catálogo Maya completo (~1900 combinaciones en
`bmc-mcp/config/categorias_maya.json`). Si el incidente no encaja en ninguna fila de
arriba:

1. No inventes una combinación de categorías que no hayas visto en esta tabla.
2. Usa la categorización operacional/producto más general y razonable que sí conozcas
   (p. ej. `Aplicacion` / `Software` para fallas de aplicativos genéricas), dejando
   claro en la nota o en tu respuesta al usuario que fue una elección aproximada.
3. Si el caso es ambiguo o crítico, prefiere preguntar antes de crear el ticket en vez
   de adivinar.

---
_Muestra generada desde `bmc-mcp/config/categorias_maya.json` (fuente: `CCTI_ARUS.xlsx`,
ambiente de pruebas) el 2026-07-29. Re-sincronizar cuando ese catálogo cambie de forma
relevante._
