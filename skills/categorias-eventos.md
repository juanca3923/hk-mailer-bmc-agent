---
name: categorias-eventos
description: Catálogo de categorización BMC Helix ARUS del dominio "eventos" (disponibilidad y capacidad de servicios de infraestructura/plataforma GTI). Cubre Incidente (eventos de disponibilidad) y Work Order (eventos de capacidad) — la subtabla decide cuál. Consúltalo cuando el caso encaje en este dominio.
---

# Categorías BMC Helix — dominio "eventos"

Tabla de datos para el dominio **eventos** (disponibilidad y capacidad de servicios
GTI: AWS, redes, aplicaciones, backup, servidores, base de datos, seguridad perimetral,
telefonía). El mapeo columna → parámetro, la traducción de Prioridad y el significado
de `¿Susceptible de cierre en mesa?` están en `guia-creacion-tickets` (sección 2) — no
se repiten aquí.

## Cómo distinguir disponibilidad de capacidad

El dominio se divide en dos subtablas según el tipo de evento — úsalas para decidir
incluso cuando el servicio afectado no aparezca literalmente en las filas:

- **Disponibilidad → Incidente**: el servicio está caído, degradado o va a caerse por
  agotamiento de un recurso — es una ausencia o falla, no algo planeado. Ejemplo: una
  alerta de disco lleno es de **disponibilidad**, porque el disco lleno hace que el
  servicio se caiga.
- **Capacidad → Requerimiento**: se pide aumentar, modificar o adicionar un recurso o
  configuración del servicio de forma planeada — el servicio sigue funcionando mientras
  se atiende. Ejemplo: aumentar la capacidad de disco de un servidor es **capacidad**,
  porque es una modificación planeada, no una falla.

Esta distinción decide el tipo de ticket para cualquier caso de este dominio (ver
`guia-creacion-tickets`, sección 1).

## Eventos de disponibilidad (Incidente)

| Tipo Servicio | Categoria Operacional 1 | Categoria Operacional 2 | Categoria Operacional 3 | Categoria de Producto 1 | Categoria de Producto 2 | Categoria de Producto 3 | Prioridad | ¿Susceptible de cierre en mesa? | Escalamiento 1 |
|---|---|---|---|---|---|---|---|---|---|
| Incidente | Aplicacion | Evento de disponibilidad | | GTI | AWS | Infraestructura | CRITICA | NO | GTI.CLOUD |
| Incidente | Aplicacion | Evento de disponibilidad | | GTI | Redes | Infraestructura | CRITICA | NO | GTI.REDES |
| Incidente | Aplicacion | Evento de disponibilidad | | GTI | Administracion de aplicaciones | Plataforma | CRITICA | NO | GTI.APLICACIONES |
| Incidente | Aplicacion | Evento de disponibilidad | | GTI | Backup | Plataforma | CRITICA | NO | GTI.BACKUPS |
| Incidente | Aplicacion | Evento de disponibilidad | | GTI | Servidor microsoft | Plataforma | CRITICA | NO | GTI.MICROSOFT |
| Incidente | Aplicacion | Evento de disponibilidad | | GTI | Seguridad perimetral | Infraestructura | CRITICA | NO | GTI.CIBERSEGURIDAD SOC |
| Incidente | Aplicacion | Evento de disponibilidad | | GTI | Base de datos | Plataforma | CRITICA | NO | GTI.DBA |
| Incidente | Aplicacion | Evento de disponibilidad | | GTI | Servidor | Linux | CRITICA | NO | GTI.LINUX |
| Incidente | Aplicacion | Evento de disponibilidad | | GTI | Virtualizacion | Plataforma | CRITICA | NO | GTI.LINUX |
| Incidente | Aplicacion | Evento de disponibilidad | | Software | Telefonia especializada | Aplicacion | CRITICA | NO | TELEFONIA |

## Eventos de capacidad (Requerimiento)

| Tipo Servicio | Categoria Operacional 1 | Categoria Operacional 2 | Categoria Operacional 3 | Categoria de Producto 1 | Categoria de Producto 2 | Categoria de Producto 3 | Prioridad | ¿Susceptible de cierre en mesa? | Escalamiento 1 |
|---|---|---|---|---|---|---|---|---|---|
| Requerimiento | Aplicacion | Evento de capacidad | | GTI | AWS | Infraestructura | CRITICO | NO | GTI.CLOUD |
| Requerimiento | Aplicacion | Evento de capacidad | | GTI | Redes | Infraestructura | CRITICO | NO | GTI.REDES |
| Requerimiento | Aplicacion | Evento de capacidad | | GTI | Administracion de aplicaciones | Plataforma | CRITICO | NO | GTI.APLICACIONES |
| Requerimiento | Aplicacion | Evento de capacidad | | GTI | Backup | Plataforma | CRITICO | NO | GTI.BACKUPS |
| Requerimiento | Aplicacion | Evento de capacidad | | GTI | Servidor microsoft | Plataforma | CRITICO | NO | GTI.MICROSOFT |
| Requerimiento | Aplicacion | Evento de capacidad | | GTI | Seguridad perimetral | Infraestructura | CRITICO | NO | GTI.CIBERSEGURIDAD SOC |
| Requerimiento | Aplicacion | Evento de capacidad | | GTI | Base de datos | Plataforma | CRITICO | NO | GTI.DBA |
| Requerimiento | Aplicacion | Evento de capacidad | | GTI | Servidor | Linux | CRITICO | NO | GTI.LINUX |
| Requerimiento | Aplicacion | Evento de capacidad | | Software | Telefonia especializada | Aplicacion | CRITICO | NO | TELEFONIA |

Nota: la subtabla de capacidad no trae fila de "Virtualizacion" (sí presente en
disponibilidad). El `Escalamiento 1` de Backup se corrigió de `GTI.BACKUP` a
`GTI.BACKUPS` (2026-09-11) para que coincida con disponibilidad: `GTI.BACKUP` no
existe como grupo real en BMC — confirmado en la corrida 4 de pruebas end-to-end,
donde ese caso quedó reasignado a `SOPORTE MESA DE SERVICIO` pese al fix de grupo
de Work Order, mientras que `GTI.BACKUPS` sí fue respetado por BMC.

Si el caso no encaja en ninguna fila de ninguna subtabla, ver `guia-creacion-tickets`
sección 3.

---
_Catálogo del dominio "eventos" entregado por la mesa de servicio el 2026-09-02;
Categoría Operacional 1/2/3 completada por la mesa de servicio el 2026-09-07.
Re-sincronizar cuando ese catálogo cambie._
