---
name: categorias-mail-drive
description: Catálogo único de categorización BMC Helix ARUS para los casos que llegan por correo (Mail Drive). Tiene dos tablas — Requerimiento (Work Order, con palabras clave para elegir la fila) e Incidente. Consúltalo siempre antes de crear un ticket; es lo único que este agente puede categorizar.
---

# Categorías BMC Helix — Mail Drive

Catálogo de los casos que entran por correo. La columna **`Tipo Servicio`** decide el
tipo de ticket: `Requerimiento` → Work Order (`bmc_create_work_order`) e `Incidente` →
Incidente (`bmc_create_incident`). El mapeo columna → parámetro está en
`guia-creacion-tickets` (sección 2). Copia siempre los valores de **una sola fila**,
tal cual (mayúsculas, tildes y espacios), sin mezclar columnas de filas distintas.
Una celda vacía significa que ese nivel no se informa. `Prioridad` (`ALTO`/`MEDIO`/`BAJO`)
se traduce a `priority` como indica la guía (sección 2); `Escalamiento 1` va vacío, así que
no pases `assigned_group` y se usa el valor por defecto de la tool.

> **Pendiente de la mesa de servicio.** La tabla original dejaba vacío el nivel de producto 3
> en tres filas de Requerimientos (`Base de datos` ×2 y `Gestiona tu Acceso`) y en los niveles
> de producto 2 y 3 de los incidentes, y la tool no acepta vacío. Se completaron con
> combinaciones que ya existen en BMC (`Base de datos` → `Plataforma`; `Gestiona tu Acceso` →
> `Aplicacion`; incidentes → la combinación de producto más cercana). Son aproximadas:
> confirmar con la mesa. `Escalamiento 1` va vacío (se usa el grupo por defecto de la tool).
>
> **Ortografía de BMC (2026-11-25).** En el catálogo de BMC la Categoría de Producto 1 se llama
> `Sofware` (sin «t») y los niveles 2 son `Sap`, `Gestiona tu acceso` y `Correo electronico`.
> Con la escritura del Excel (`Software`, `SAP`, …) el ticket se crea, pero BMC no deja cerrarlo
> («Debe completar las categorías Operativa y de Producto»). Las filas de Requerimientos usan la
> escritura de BMC; cuando BMC corrija `Sofware` → `Software`, revertir. La tabla de Incidentes
> no se ha validado contra el cierre.

## Requerimientos (Work Order)

**Regla restrictiva (2026-11-25): una fila aplica SOLO si el correo nombra explícitamente el sistema o
producto de esa fila** — alguna de sus palabras clave de producto o su Categoría de Producto 2 (DA/Directorio
Activo, Sharepoint/Teams/unidad de red, VPN/Firewall/servidor…, SAP, Base de datos, Prisma, telefonía, MFA,
correo/licencia). Las **palabras de acción** (`crear usuario`, `creación de usuario`, `nuevo usuario`, `alta de
usuario`, `permisos`, `contraseña`, `clave`) describen *qué* se pide, no *dónde*: solas **no bastan** para elegir una
fila. En «Asignar Permisos», pedir permisos y crear un usuario se interpretan igual (por eso esas palabras están en
todas sus filas), pero siempre junto a un sistema nombrado.

- **Prohibido deducir por conocimiento propio** que una aplicación usa otro sistema (p. ej. «Mosaico inicia sesión con el
  Directorio Activo»): solo cuenta lo que el correo dice textualmente.
- Si el sistema nombrado **no está** en esta tabla, o el correo no nombra ninguno → **Work Order por defecto
  `MailDrive`** (`guia-creacion-tickets`, sección 1). No hay fila «aproximada».
- Si dos filas encajan por igual porque el correo nombra ambos sistemas, elige la más específica y deja explícito que
  fue una elección aproximada.

Ejemplos:

| Correo | Resultado |
|---|---|
| «Crear el usuario X en el Directorio Activo» | fila `Asignar Permisos` / `Directorio Activo` |
| «Crear los usuarios X e Y en la aplicación Mosaico» | por defecto `MailDrive` (Mosaico no está en el catálogo) |
| «Dar acceso a la carpeta compartida / unidad de red» | fila `Asignar Permisos` / `Servidor microsoft` |
| «Necesito una contraseña nueva» (sin decir de qué sistema) | por defecto `MailDrive` |

| Tipo Servicio | Categoria Operacional 1 | Categoria Operacional 2 | Categoria Operacional 3 | Categoria de Producto 1 | Categoria de Producto 2 | Categoria de Producto 3 | Prioridad | Escalamiento 1 | Palabras clave |
|---|---|---|---|---|---|---|---|---|---|
| Requerimiento | Aplicacion | Asignar Permisos |  | GTI | Directorio Activo | Plataforma | MEDIO |  | DA, Directorio Activo, crear usuario, crear usuarios, creación de usuario, creación de usuarios, creacion de usuario, nuevo usuario, alta de usuario |
| Requerimiento | Aplicacion | Asignar Permisos |  | GTI | Servidor microsoft | Plataforma | MEDIO |  | Sharepoint, teams, unidad de red, crear usuario, crear usuarios, creación de usuario, creación de usuarios, creacion de usuario, nuevo usuario, alta de usuario |
| Requerimiento | Aplicacion | Asignar Permisos |  | GTI | Seguridad perimetral | Infraestructura | MEDIO |  | SSL, IP, TCP, UDP, SFTP, Conectividad, API, alcance, servidor, servidores, acceso, accesos, puerto, puertos, ssh, VPN, AP, clearpass, salida a internet, FAC, Fase, Client to site, SW, ROUTER, FIREWALL, FW, Enlace, crear usuario, crear usuarios, creación de usuario, creación de usuarios, creacion de usuario, nuevo usuario, alta de usuario |
| Requerimiento | Aplicacion | Asignar Permisos |  | GTI | Plataforma | SAP | MEDIO |  | Orden transporte, Mandante, OT, Acceso a transacción, SAP, ARDK, crear usuario, crear usuarios, creación de usuario, creación de usuarios, creacion de usuario, nuevo usuario, alta de usuario |
| Requerimiento | Aplicacion | Asignar Permisos |  | GTI | Base de datos | Plataforma | MEDIO |  | crear usuario, crear usuarios, creación de usuario, creación de usuarios, creacion de usuario, nuevo usuario, alta de usuario |
| Requerimiento | Aplicacion | Crear / cambiar contraseña |  | Sofware | Telefonia especializada | Aplicacion | ALTO |  | haxahud, queuemetrics, telefonia |
| Requerimiento | Aplicacion | Crear / cambiar contraseña |  | Sofware | Prisma | Aplicacion | ALTO |  | Prisma |
| Requerimiento | Aplicacion | Crear / cambiar contraseña |  | GTI | Base de datos | Plataforma | ALTO |  | BD, Base de Datos, Base datos |
| Requerimiento | Aplicacion | Crear / cambiar contraseña |  | Sofware | Sap | Aplicacion | MEDIO |  | Orden transporte, Mandante, OT, Acceso a transacción, SAP, ARDK, Contraseña, clave |
| Requerimiento | Aplicacion | Instalar agente MFA |  | Sofware | Gestiona tu acceso | Aplicacion | MEDIO |  | MFA, Doble Factor, authenticator, multifactor |
| Requerimiento | Aplicacion | Asignar / modificar licencia |  | Sofware | Correo electronico | Aplicacion | MEDIO |  | licencia, correo, E1, E5, licenciamiento |

## Incidentes

Los incidentes no traen palabras clave.

| Tipo Servicio | Categoria Operacional 1 | Categoria Operacional 2 | Categoria Operacional 3 | Categoria de Producto 1 | Categoria de Producto 2 | Categoria de Producto 3 | Prioridad | Escalamiento 1 |
|---|---|---|---|---|---|---|---|---|
| Incidente | Aplicacion | Falla Aplicacion | | Software | Telefonia especializada | Aplicacion | | |
| Incidente | Aplicacion | Bloqueo Aplicacion | | GTI | Administracion de aplicaciones | Plataforma | | |
| Incidente | Aplicacion | Falla Acceso | | Software | Gestiona tu acceso | Aplicacion | | |
| Incidente | Aplicacion | Falla salida / entrada de llamadas | | Software | Telefonia especializada | Aplicacion | | |

Si el caso no encaja en ninguna fila de estas dos tablas, ver `guia-creacion-tickets`
sección 1 (Work Order por defecto `MailDrive`, para triage manual); nunca crees un Incidente fuera de
la tabla de incidentes.

---
_Catálogo "Categorización Mail Drive" entregado por la mesa de servicio. Re-sincronizar
cuando cambie._
