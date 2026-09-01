---
name: categorias-requerimientos
description: Catálogo de categorías BMC Helix ARUS para crear Work Orders (Requerimientos). Consulta siempre antes de llamar bmc_create_work_order.
---

# Categorías BMC Helix — Requerimiento (Work Order)

Tabla de datos para `bmc_create_work_order`. El mapeo columna → parámetro, la
traducción de Prioridad ES→EN y qué hacer si el caso no encaja en ninguna fila están en
`guia-creacion-tickets` (secciones 2 y 3) — no se repiten aquí.

## Muestra de categorías (ambiente de pruebas arus-dev)

Esta tabla es una **muestra pequeña e ilustrativa**, no el catálogo completo. Sale de
`config/categorias_maya.json` en `bmc-mcp` (generado desde `CCTI_ARUS.xlsx`, el Excel
del **ambiente de pruebas**; el propio dato aclara que el emparejamiento categoría
operacional↔producto es mecánico y no representa una caracterización ITSM formal).
Cubre los escenarios más comunes de un área de TI: usuarios/telefonía, cambio de
contraseña, accesos/instalaciones y solicitudes generales.

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

Esta muestra **no reemplaza** el catálogo Maya completo (~1900 combinaciones en
`bmc-mcp/config/categorias_maya.json`). Si el requerimiento no encaja en ninguna fila,
ver `guia-creacion-tickets` sección 3.

---
_Muestra generada desde `bmc-mcp/config/categorias_maya.json` (fuente: `CCTI_ARUS.xlsx`,
ambiente de pruebas) el 2026-07-29. Re-sincronizar cuando ese catálogo cambie de forma
relevante._
