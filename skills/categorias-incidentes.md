---
name: categorias-incidentes
description: Catálogo de categorías BMC Helix ARUS para crear Incidentes. Consulta siempre antes de llamar bmc_create_incident.
---

# Categorías BMC Helix — Incidente

Tabla de datos para `bmc_create_incident`. El mapeo columna → parámetro y qué hacer si
el caso no encaja en ninguna fila están en `guia-creacion-tickets` (secciones 2 y 3) —
no se repiten aquí.

`impact` y `urgency` **no son parámetros** de `bmc_create_incident`: todo incidente
creado por este agente queda fijo en Impact `1-Extensive/Widespread` / Urgency
`1-Critical`.

## Muestra de categorías (ambiente de pruebas arus-dev)

Esta tabla es una **muestra pequeña e ilustrativa**, no el catálogo completo. Sale de
`config/categorias_maya.json` en `bmc-mcp` (generado desde `CCTI_ARUS.xlsx`, el Excel
del **ambiente de pruebas**; el propio dato aclara que el emparejamiento categoría
operacional↔producto es mecánico y no representa una caracterización ITSM formal).
Cubre los escenarios más comunes de un área de TI: usuarios/telefonía, cambio de
contraseña, caída de aplicaciones y solicitudes generales.

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

Esta muestra **no reemplaza** el catálogo Maya completo (~1900 combinaciones en
`bmc-mcp/config/categorias_maya.json`). Si el incidente no encaja en ninguna fila, ver
`guia-creacion-tickets` sección 3.

---
_Muestra generada desde `bmc-mcp/config/categorias_maya.json` (fuente: `CCTI_ARUS.xlsx`,
ambiente de pruebas) el 2026-07-29. Re-sincronizar cuando ese catálogo cambie de forma
relevante._
