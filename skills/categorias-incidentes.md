---
name: categorias-incidentes
description: Catálogo oficial de categorías BMC Helix ARUS para crear Incidentes. Consulta siempre antes de llamar create_incident.
---

# Categorías BMC Helix — Incidente

Usa esta guía para seleccionar la combinación **exacta** de campos de categorización
al crear un **incidente** con `create_incident`.

## Campos que debes completar

| Parámetro en `create_incident` | Columna en esta guía |
|-------------------------------|---------------------|
| `categorization_tier_1` | Cat Op 1 |
| `categorization_tier_2` | Cat Op 2 |
| `categorization_tier_3` | dejar vacío `""` siempre |
| `product_categorization_tier_1` | Cat Prod 1 |
| `product_categorization_tier_2` | Cat Prod 2 |
| `product_categorization_tier_3` | Cat Prod 3 |
| `impact` / `urgency` | derivar de Prioridad (ver tabla abajo) |

### Mapeo Prioridad → impact / urgency

| Prioridad | impact | urgency |
|-----------|--------|---------|
| CRITICA | `1-Extensive/Widespread` | `1-Critical` |
| ALTA | `2-Significant/Large` | `2-High` |
| MEDIA | `3-Moderate/Limited` | `3-Medium` |
| BAJA | `4-Minor/Localized` | `4-Low` |

> **Regla:** elige la fila que mejor describe el caso del usuario.
> Copia los valores **exactamente** como aparecen en la tabla.
> Cat Op 3 (`categorization_tier_3`) siempre va vacío `""`.

## Administrativos

| Cat Op 2 | Cat Prod 1 | Cat Prod 2 | Cat Prod 3 | Prioridad |
|----------|-----------|-----------|-----------|-----------|
| Daño tarjeta de acceso | Proceso de negocio | Tarjeta de acceso | Carne | MEDIA |
| Reportar Perdida/ hurto | Proceso de negocio | Tarjeta de acceso | Carne | MEDIA |

## Aplicacion

| Cat Op 2 | Cat Prod 1 | Cat Prod 2 | Cat Prod 3 | Prioridad |
|----------|-----------|-----------|-----------|-----------|
| Agente no reporta en aplicativo | Software | Herramienta de gestion | Aplicacion | BAJA |
| Alertamiento espacio en disco | Software | Nemesis | Aplicacion | MEDIA |
| Aplicacion caida | Software | Herramienta de gestion | Aplicacion | BAJA |
| Aplicacion no notifica | Software | Herramienta de gestion | Aplicacion | BAJA |
| Asistente cierra tareas sin gestion | Software | RPA accesos | Aplicacion | MEDIA |
| Asistente no crea tareas | Software | RPA accesos | Aplicacion | ALTA |
| Asistente suspende tareas | Software | RPA accesos | Aplicacion | MEDIA |
| Bloqueo aplicacion | Software | Correo electronico | Aplicacion | BAJA |
| Bloqueo de agente en planta | Software | Telefonia especializada | Aplicacion | BAJA |
| Caida aplicacion | Software | One drive | Aplicacion | BAJA |
| Caida aplicación | Software | Datarus | Aplicacion | MEDIA |
| Caida de la aplicacion | Software | Datarus | Aplicacion | CRITICA |
| Caida de la aplicacion | Software | Forticlient | Aplicacion | CRITICA |
| Caida de la aplicacion | Software | Nemesis | Aplicacion | CRITICA |
| Caida de la aplicacion | Software | Prisma | Aplicacion | CRITICA |
| Caida de la aplicacion | Software | Teams | Aplicacion | CRITICA |
| Caida del Aplicativo | Software | Herramienta de gestion | Aplicacion | BAJA |
| Caida del servicio | Software | Bisourcing | Aplicacion | CRITICA |
| Caida del servicio | Software | Bizagi bpm Compras | Aplicacion | CRITICA |
| Caida del servicio | Software | Bizagi bpm Cotizadores | Aplicacion | ALTA |
| Caida del servicio | Software | Buk | Aplicacion | CRITICA |
| Caida del servicio | Software | Efi activos | Aplicacion | CRITICA |
| Caida del servicio | Software | Efi alfa | Aplicacion | CRITICA |
| Caida del servicio | Software | Efi alinea2 | Aplicacion | CRITICA |
| Caida del servicio | Software | Efi cuentas por pagar | Aplicacion | CRITICA |
| Caida del servicio | Software | Efi dedicacion de horas y subrepartos | Aplicacion | CRITICA |
| Caida del servicio | Software | Efi prefacturador | Aplicacion | CRITICA |
| Caida del servicio | Software | Efi presupuesto | Aplicacion | CRITICA |
| Caida del servicio | Software | Efi telefonia | Aplicacion | CRITICA |
| Caida del servicio | Software | FE Cadena | Aplicacion | CRITICA |
| Caida del servicio | Software | Gestiona tu acceso | Aplicacion | CRITICA |
| Caida del servicio | Software | Iris | Aplicacion | CRITICA |
| Caida del servicio | Software | Kiosko | Aplicacion | CRITICA |
| Caida del servicio | Software | La U | Aplicacion | CRITICA |
| Caida del servicio | Software | Mosaico Administrativo Indicadores | Aplicacion | CRITICA |
| Caida del servicio | Software | Mosaico Administrativo Registro Visitantes | Aplicacion | CRITICA |
| Caida del servicio | Software | Nomus | Aplicacion | CRITICA |
| Caida del servicio | Software | Pentaho | Aplicacion | CRITICA |
| Caida del servicio | Software | Prometeo | Aplicacion | ALTA |
| Caida del servicio | Software | Salesforce | Aplicacion | CRITICA |
| Caida del servicio | Software | Sap | Aplicacion | CRITICA |
| Caida del servicio | Software | Telefonia administrativa | Aplicacion | CRITICA |
| Caida del servicio | Software | Tienda ARUS | Aplicacion | CRITICA |
| Caida del servicio (indisponibilidad) | Software | Auditoria de accesos | Aplicacion | MEDIA |
| Caida planta telefonica | Software | Telefonia especializada | Aplicacion | CRITICA |
| Desincronizacion de token  | Software | Vital E | Aplicacion | BAJA |
| Encolamiento de llamadas | Software | Telefonia administrativa | Aplicacion | ALTA |
| Encolamiento de llamadas | Software | Telefonia especializada | Aplicacion | ALTA |
| Error al cargar imágenes | Software | Datarus | Aplicacion | MEDIA |
| Error al cargar lote | Software | CMI Sura | Aplicacion | MEDIA |
| Error al cargar lote | Software | Rips | Aplicacion | MEDIA |
| Error convirtiendo imagenes y archivos | Software | Datarus | Aplicacion | MEDIA |
| Error convirtiendo imagenes y archivos | Software | Datarus | Aplicacion | ALTA |
| Error de datos | Software | Kiosko | Aplicacion | MEDIA |
| Error de datos | Software | La U | Aplicacion | MEDIA |
| Error de datos | Software | Mosaico Administrativo Indicadores | Aplicacion | MEDIA |
| Error de datos | Software | Mosaico Administrativo Registro Visitantes | Aplicacion | MEDIA |
| Error de datos | Software | Nomus | Aplicacion | ALTA |
| Error de datos | Software | Pentaho | Aplicacion | ALTA |
| Error de datos | Software | Salesforce | Aplicacion | ALTA |
| Error de datos | Software | Sap | Aplicacion | MEDIA |
| Error de datos | Software | Tienda ARUS | Aplicacion | ALTA |
| Error de ingreso portal de autoservicio | Software | Herramienta de gestion | Aplicacion | BAJA |
| Error de radicacion | Software | Rips | Aplicacion | MEDIA |
| Error en codigo cups | Software | Rips | Aplicacion | MEDIA |
| Error en la interfaz de usuario | Software | Herramienta de gestion | Aplicacion | BAJA |
| Error en la medicion de metricas | Software | Herramienta de gestion | Aplicacion | BAJA |
| Error en la oferta de catalogo de servicio | Software | Herramienta de gestion | Aplicacion | BAJA |
| Error en los datos de dynabodb | Software | CMI Sura | Aplicacion | ALTA |
| Error en los datos del aplicativo | Software | Herramienta de gestion | Aplicacion | BAJA |
| Error exportando informacion | Software | Nemesis | Aplicacion | MEDIA |
| Error funcional | GTI | Directorio activo | Plataforma | MEDIA |
| Error funcional | Software | Efi activos | Aplicacion | BAJA |
| Error funcional | Software | Efi alfa | Aplicacion | BAJA |
| Error funcional | Software | Efi alinea2 | Aplicacion | BAJA |
| Error funcional | Software | Efi cuentas por pagar | Aplicacion | BAJA |
| Error funcional | Software | Efi dedicacion de horas y subrepartos | Aplicacion | BAJA |
| Error funcional | Software | Efi prefacturador | Aplicacion | BAJA |
| Error funcional | Software | Efi presupuesto | Aplicacion | BAJA |
| Error funcional | Software | Efi telefonia | Aplicacion | BAJA |
| Error funcional | Software | Rips | Aplicacion | MEDIA |
| Error funcionamiento de flujo | Software | Herramienta de gestion | Aplicacion | BAJA |
| Error malla validadora | Software | Rips | Aplicacion | MEDIA |
| Errores en interfaz | Software | Efi activos | Aplicacion | MEDIA |
| Errores en interfaz | Software | Efi alfa | Aplicacion | MEDIA |
| Errores en interfaz | Software | Efi alinea2 | Aplicacion | MEDIA |
| Errores en interfaz | Software | Efi cuentas por pagar | Aplicacion | MEDIA |
| Errores en interfaz | Software | Efi dedicacion de horas y subrepartos | Aplicacion | MEDIA |
| Errores en interfaz | Software | Efi prefacturador | Aplicacion | MEDIA |
| Errores en interfaz | Software | Efi presupuesto | Aplicacion | MEDIA |
| Errores en interfaz | Software | Efi telefonia | Aplicacion | MEDIA |
| Errores en interfaz | Software | FE Cadena | Aplicacion | CRITICA |
| Evento de disponibilidad | Software | Telefonia especializada | Aplicacion | CRITICA |
| Extension muda | Software | Telefonia administrativa | Aplicacion | ALTA |
| Extension muda | Software | Telefonia especializada | Aplicacion | ALTA |
| Falla al consultar lote | Software | Datarus | Aplicacion | MEDIA |
| Falla al ejecutar reporte | Software | Prisma | Aplicacion | BAJA |
| Falla al ejecutar reporte | Software | Telefonia administrativa | Aplicacion | BAJA |
| Falla al enviar | Software | Correo electronico | Aplicacion | MEDIA |
| Falla al guardar lote | Software | Datarus | Aplicacion | MEDIA |
| Falla aplicacion | Software | Bisourcing | Aplicacion | CRITICA |
| Falla aplicacion | Software | Bizagi bpm Compras | Aplicacion | ALTA |
| Falla aplicacion | Software | Bizagi bpm Cotizadores | Aplicacion | ALTA |
| Falla aplicacion | Software | Buk | Aplicacion | MEDIA |
| Falla aplicacion | Software | CMI Sura | Aplicacion | ALTA |
| Falla aplicacion | Software | Consola de monitoreo | Aplicacion | ALTA |
| Falla aplicacion | Software | Correo electronico | Aplicacion | MEDIA |
| Falla aplicacion | Software | Datarus | Aplicacion | MEDIA |
| Falla aplicacion | Software | Iris | Aplicacion | ALTA |
| Falla aplicacion | Software | Kiosko | Aplicacion | ALTA |
| Falla aplicacion | Software | La U | Aplicacion | ALTA |
| Falla aplicacion | Software | Mosaico Administrativo Indicadores | Aplicacion | CRITICA |
| Falla aplicacion | Software | Mosaico Administrativo Registro Visitantes | Aplicacion | CRITICA |
| Falla aplicacion | Software | Nemesis | Aplicacion | MEDIA |
| Falla aplicacion | Software | Nomus | Aplicacion | ALTA |
| Falla aplicacion | Software | Pentaho | Aplicacion | MEDIA |
| Falla aplicacion | Software | Prisma | Aplicacion | MEDIA |
| Falla aplicacion | Software | Salesforce | Aplicacion | ALTA |
| Falla aplicacion | Software | Sap | Aplicacion | ALTA |
| Falla aplicacion | Software | Teams | Aplicacion | MEDIA |
| Falla aplicacion | Software | Tienda ARUS | Aplicacion | MEDIA |
| Falla auditoria de accesos | Software | Auditoria de accesos | Aplicacion | ALTA |
| Falla auditoria usuarios | Software | Auditoria de accesos | Aplicacion | ALTA |
| Falla autenticacion cuenta | Software | Nemesis | Aplicacion | ALTA |
| Falla autenticacion/acceso | Software | Herramienta de gestion | Aplicacion | BAJA |
| Falla dataentry | Software | Nemesis | Aplicacion | MEDIA |
| Falla de acceso | Software | Auditoria de accesos | Aplicacion | MEDIA |
| Falla de acceso | Software | Datarus | Aplicacion | BAJA |
| Falla de acceso | Software | Efi activos | Aplicacion | ALTA |
| Falla de acceso | Software | Efi alfa | Aplicacion | ALTA |
| Falla de acceso | Software | Efi alinea2 | Aplicacion | ALTA |
| Falla de acceso | Software | Efi cuentas por pagar | Aplicacion | ALTA |
| Falla de acceso | Software | Efi dedicacion de horas y subrepartos | Aplicacion | ALTA |
| Falla de acceso | Software | Efi prefacturador | Aplicacion | ALTA |
| Falla de acceso | Software | Efi presupuesto | Aplicacion | ALTA |
| Falla de acceso | Software | Efi telefonia | Aplicacion | ALTA |
| Falla de acceso | Software | FE Cadena | Aplicacion | ALTA |
| Falla de acceso | Software | Iris | Aplicacion | ALTA |
| Falla de acceso | Software | La U | Aplicacion | ALTA |
| Falla de acceso | Software | Mosaico Administrativo Indicadores | Aplicacion | MEDIA |
| Falla de acceso | Software | Mosaico Administrativo Registro Visitantes | Aplicacion | MEDIA |
| Falla de acceso | Software | Nemesis | Aplicacion | MEDIA |
| Falla de acceso | Software | Nomus | Aplicacion | ALTA |
| Falla de acceso | Software | Pentaho | Aplicacion | ALTA |
| Falla de acceso | Software | Prisma | Aplicacion | ALTA |
| Falla de acceso | Software | Salesforce | Aplicacion | ALTA |
| Falla de acceso | Software | Sap | Aplicacion | MEDIA |
| Falla de acceso | Software | Telefonia especializada | Aplicacion | BAJA |
| Falla de acceso | Software | Tienda ARUS | Aplicacion | MEDIA |
| Falla de aplicacion | GTI | Directorio activo | Plataforma | MEDIA |
| Falla de aplicacion | Software | Telefonia especializada | Aplicacion | ALTA |
| Falla de audio | Software | Telefonia especializada | Aplicacion | ALTA |
| Falla de autenticacion | Software | Bizagi bpm Compras | Aplicacion | MEDIA |
| Falla de autenticacion | Software | Bizagi bpm Cotizadores | Aplicacion | ALTA |
| Falla de autenticacion vpn | Software | Forticlient | Aplicacion | MEDIA |
| Falla de bases de datos Hana | Software | Sap | Aplicacion | ALTA |
| Falla de conexion /conexion inestable vpn | Software | Forticlient | Aplicacion | ALTA |
| Falla de configuracion de disponibilidad | Software | Telefonia administrativa | Aplicacion | ALTA |
| Falla de la aplicacion | Software | Forticlient | Aplicacion | ALTA |
| Falla de navegacion por vpn | Software | Forticlient | Aplicacion | ALTA |
| Falla de recepcion | Software | Correo electronico | Aplicacion | ALTA |
| Falla de sincronizacion | Software | Office 365 | Aplicacion | BAJA |
| Falla direccionamiento de llamadas | Software | Telefonia administrativa | Aplicacion | CRITICA |
| Falla direccionamiento de llamadas | Software | Telefonia especializada | Aplicacion | CRITICA |
| Falla ejecutar reporte | Software | Kiosko | Aplicacion | MEDIA |
| Falla ejecutar reporte | Software | La U | Aplicacion | MEDIA |
| Falla ejecutar reporte | Software | Mosaico Administrativo Indicadores | Aplicacion | MEDIA |
| Falla ejecutar reporte | Software | Mosaico Administrativo Registro Visitantes | Aplicacion | MEDIA |
| Falla ejecutar reporte | Software | Nomus | Aplicacion | ALTA |
| Falla ejecutar reporte | Software | Pentaho | Aplicacion | MEDIA |
| Falla ejecutar reporte | Software | Tienda ARUS | Aplicacion | BAJA |
| Falla en adjuntos | Software | Bizagi bpm Compras | Aplicacion | ALTA |
| Falla en adjuntos | Software | Bizagi bpm Cotizadores | Aplicacion | ALTA |
| Falla en dashboard | Software | Gobierno de datos | Aplicacion | BAJA |
| Falla en ejecutar reporte | Software | Datarus | Aplicacion | MEDIA |
| Falla en ejecutar reporte | Software | Iris | Aplicacion | MEDIA |
| Falla en ejecutar reporte | Software | Nemesis | Aplicacion | MEDIA |
| Falla en el calendario | Software | Correo electronico | Aplicacion | MEDIA |
| Falla en el servidor de consola | Software | Consola de monitoreo | Aplicacion | CRITICA |
| Falla en guardar en memoria cache | Software | Datarus | Aplicacion | MEDIA |
| Falla en importacion Vscan | Software | Datarus | Aplicacion | MEDIA |
| Falla en la ejecucion | Software | RPA Compras | Aplicacion | ALTA |
| Falla en la ejecucion | Software | RPA Contabilidad | Aplicacion | ALTA |
| Falla en la ejecucion | Software | RPA Facturacion | Aplicacion | ALTA |
| Falla en las integraciones | Software | Efi activos | Aplicacion | ALTA |
| Falla en las integraciones | Software | Efi alfa | Aplicacion | ALTA |
| Falla en las integraciones | Software | Efi alinea2 | Aplicacion | ALTA |
| Falla en las integraciones | Software | Efi cuentas por pagar | Aplicacion | ALTA |
| Falla en las integraciones | Software | Efi dedicacion de horas y subrepartos | Aplicacion | ALTA |
| Falla en las integraciones | Software | Efi prefacturador | Aplicacion | ALTA |
| Falla en las integraciones | Software | Efi presupuesto | Aplicacion | ALTA |
| Falla en las integraciones | Software | Efi telefonia | Aplicacion | ALTA |
| Falla en las integraciones | Software | FE Cadena | Aplicacion | MEDIA |
| Falla en radicacion | Software | Nemesis | Aplicacion | MEDIA |
| Falla en recepcion | Software | Nemesis | Aplicacion | MEDIA |
| Falla exportando captura de cabecera | Software | Datarus | Aplicacion | MEDIA |
| Falla exportando captura de indices | Software | Datarus | Aplicacion | MEDIA |
| Falla funcional | Software | Gestiona tu acceso | Aplicacion | CRITICA |
| Falla funcional | Software | Prometeo | Aplicacion | ALTA |
| Falla importacion | Software | Datarus | Aplicacion | ALTA |
| Falla importacion | Software | Datarus | Aplicacion | MEDIA |
| Falla importacion | Software | Nemesis | Aplicacion | MEDIA |
| Falla modulo almacenamiento | Software | Nemesis | Aplicacion | MEDIA |
| Falla modulo asesor | Software | Nemesis | Aplicacion | MEDIA |
| Falla modulo calidad | Software | Nemesis | Aplicacion | MEDIA |
| Falla modulo gesdoceo | Software | Nemesis | Aplicacion | MEDIA |
| Falla modulo suratep | Software | Nemesis | Aplicacion | MEDIA |
| Falla modulo visor web | Software | Nemesis | Aplicacion | MEDIA |
| Falla procesos de ausentismos | Software | RPA accesos | Aplicacion | ALTA |
| Falla reporte | Software | Vital E | Aplicacion | BAJA |
| Falla salida/entrada de llamadas | Software | Telefonia administrativa | Aplicacion | CRITICA |
| Falla salida/entrada de llamadas | Software | Telefonia especializada | Aplicacion | CRITICA |
| Fallas en contador de imagenes | Software | Datarus | Aplicacion | MEDIA |
| Fallas en contador de imagenes | Software | Nemesis | Aplicacion | MEDIA |
| Fallas para subir a p8 | Software | Nemesis | Aplicacion | MEDIA |
| Falle generando reportes | Software | Nemesis | Aplicacion | MEDIA |
| Imagenes no pasan a Datarus | Software | Datarus | Aplicacion | MEDIA |
| Imagenes salen degradadas | Software | Datarus | Aplicacion | MEDIA |
| Incidente | Software | Mosaico | Aplicacion | ALTA |
| Incidente de seguridad | Software | Auditoria de accesos | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Bisourcing | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Bizagi bpm Compras | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Bizagi bpm Cotizadores | Aplicacion | ALTA |
| Incidente de seguridad | Software | Buk | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Efi activos | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Efi alfa | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Efi alinea2 | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Efi cuentas por pagar | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Efi dedicacion de horas y subrepartos | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Efi prefacturador | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Efi presupuesto | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Efi telefonia | Aplicacion | CRITICA |
| Incidente de seguridad | Software | FE Cadena | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Iris | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Kiosko | Aplicacion | CRITICA |
| Incidente de seguridad | Software | La U | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Mosaico Administrativo Indicadores | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Mosaico Administrativo Registro Visitantes | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Nemesis | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Nomus | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Pentaho | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Salesforce | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Sap | Aplicacion | CRITICA |
| Incidente de seguridad | Software | Tienda ARUS | Aplicacion | CRITICA |
| Inconsistencia de datos personales | Software | Iris | Aplicacion | ALTA |
| Inconsistencia de datos personales | Software | Pentaho | Aplicacion | MEDIA |
| Inconsistencia en datos personales | Software | La U | Aplicacion | MEDIA |
| Inconsistencia en datos personales | Software | Prisma | Aplicacion | BAJA |
| Inconsistencia en la ejecucion | Software | RPA Compras | Aplicacion | ALTA |
| Inconsistencia en la ejecucion | Software | RPA Contabilidad | Aplicacion | ALTA |
| Inconsistencia en la ejecucion | Software | RPA Facturacion | Aplicacion | ALTA |
| Inconsistencia en los reportes | Software | Herramienta de gestion | Aplicacion | BAJA |
| Intermitencia en la comunicacion | Software | Telefonia administrativa | Aplicacion | ALTA |
| Intermitencia en la comunicacion | Software | Telefonia especializada | Aplicacion | ALTA |
| Lentitud aplicacion | Software | Auditoria de accesos | Aplicacion | BAJA |
| Lentitud aplicacion | Software | Bisourcing | Aplicacion | ALTA |
| Lentitud aplicacion | Software | Bizagi bpm Compras | Aplicacion | BAJA |
| Lentitud aplicacion | Software | Bizagi bpm Cotizadores | Aplicacion | ALTA |
| Lentitud aplicacion | Software | Buk | Aplicacion | BAJA |
| Lentitud aplicacion | Software | Correo electronico | Aplicacion | MEDIA |
| Lentitud aplicacion | Software | Efi activos | Aplicacion | MEDIA |
| Lentitud aplicacion | Software | Efi alfa | Aplicacion | MEDIA |
| Lentitud aplicacion | Software | Efi alinea2 | Aplicacion | MEDIA |
| Lentitud aplicacion | Software | Efi cuentas por pagar | Aplicacion | MEDIA |
| Lentitud aplicacion | Software | Efi dedicacion de horas y subrepartos | Aplicacion | MEDIA |
| Lentitud aplicacion | Software | Efi prefacturador | Aplicacion | MEDIA |
| Lentitud aplicacion | Software | Efi presupuesto | Aplicacion | MEDIA |
| Lentitud aplicacion | Software | Efi telefonia | Aplicacion | MEDIA |
| Lentitud aplicacion | Software | FE Cadena | Aplicacion | MEDIA |
| Lentitud aplicacion | Software | Iris | Aplicacion | ALTA |
| Lentitud aplicacion | Software | Kiosko | Aplicacion | MEDIA |
| Lentitud aplicacion | Software | La U | Aplicacion | ALTA |
| Lentitud aplicacion | Software | Mosaico Administrativo Indicadores | Aplicacion | MEDIA |
| Lentitud aplicacion | Software | Mosaico Administrativo Registro Visitantes | Aplicacion | MEDIA |
| Lentitud aplicacion | Software | Nomus | Aplicacion | BAJA |
| Lentitud aplicacion | Software | Pentaho | Aplicacion | ALTA |
| Lentitud aplicacion | Software | Salesforce | Aplicacion | ALTA |
| Lentitud aplicacion | Software | Sap | Aplicacion | ALTA |
| Lentitud aplicacion | Software | Tienda ARUS | Aplicacion | MEDIA |
| Lentitud en aplicacion | Software | Vital E | Aplicacion | BAJA |
| Lentitud en el aplicativo | Software | Herramienta de gestion | Aplicacion | BAJA |
| Lentitud en la aplicacion | Software | Datarus | Aplicacion | BAJA |
| Lentitud en la aplicacion | Software | Nemesis | Aplicacion | BAJA |
| Lentitud en la aplicacion | Software | Prisma | Aplicacion | ALTA |
| Lentitud en la aplicación | Software | Datarus | Aplicacion | MEDIA |
| Lote no aparece | Software | Datarus | Aplicacion | ALTA |
| Lote no aparece | Software | Nemesis | Aplicacion | MEDIA |
| Lote no llegan a carpetas | Software | Nemesis | Aplicacion | MEDIA |
| Lote no sale | Software | Nemesis | Aplicacion | MEDIA |
| Lotes bloqueando procesos | Software | Nemesis | Aplicacion | MEDIA |
| Lotes no llegan a carpetas | Software | Datarus | Aplicacion | MEDIA |
| Lotes no sales a nemesis | Software | Datarus | Aplicacion | MEDIA |
| No carga informacion | Software | Datarus | Aplicacion | MEDIA |
| No carga informacion | Software | Efi activos | Aplicacion | MEDIA |
| No carga informacion | Software | Efi alfa | Aplicacion | MEDIA |
| No carga informacion | Software | Efi alinea2 | Aplicacion | MEDIA |
| No carga informacion | Software | Efi cuentas por pagar | Aplicacion | MEDIA |
| No carga informacion | Software | Efi dedicacion de horas y subrepartos | Aplicacion | MEDIA |
| No carga informacion | Software | Efi prefacturador | Aplicacion | MEDIA |
| No carga informacion | Software | Efi presupuesto | Aplicacion | MEDIA |
| No carga informacion | Software | Efi telefonia | Aplicacion | MEDIA |
| No carga informacion | Software | FE Cadena | Aplicacion | MEDIA |
| No carga informacion | Software | Iris | Aplicacion | MEDIA |
| No carga informacion | Software | Kiosko | Aplicacion | MEDIA |
| No carga informacion | Software | La U | Aplicacion | BAJA |
| No carga informacion | Software | Mosaico Administrativo Indicadores | Aplicacion | BAJA |
| No carga informacion | Software | Mosaico Administrativo Registro Visitantes | Aplicacion | BAJA |
| No carga informacion | Software | Nemesis | Aplicacion | MEDIA |
| No carga informacion | Software | Nomus | Aplicacion | ALTA |
| No carga informacion | Software | One drive | Aplicacion | BAJA |
| No carga informacion | Software | Pentaho | Aplicacion | MEDIA |
| No carga informacion | Software | Prisma | Aplicacion | CRITICA |
| No carga informacion | Software | Tienda ARUS | Aplicacion | MEDIA |
| No carga informacion | Software | Vital E | Aplicacion | BAJA |
| No carga url | Software | Herramienta de gestion | Aplicacion | BAJA |
| No descarga adjuntos | Software | Correo electronico | Aplicacion | MEDIA |
| No descarga adjuntos | Software | Teams | Aplicacion | BAJA |
| No permite grabar lotes | Software | CMI Sura | Aplicacion | MEDIA |
| No permite grabar lotes | Software | Nemesis | Aplicacion | MEDIA |
| No se puede visualizar informacion | Software | Herramienta de gestion | Aplicacion | BAJA |
| Voz entrecortada | Software | Telefonia administrativa | Aplicacion | ALTA |

## Equipos Tecnologicos

| Cat Op 2 | Cat Prod 1 | Cat Prod 2 | Cat Prod 3 | Prioridad |
|----------|-----------|-----------|-----------|-----------|
| Atasco de papel | Hardware | Impresion | Impresora | MEDIA |
| Bloqueo BitLocker/Absolute | Hardware | Estacion de trabajo | Computador | ALTA |
| Daño camara | Hardware | Estacion de trabajo | Computador | MEDIA |
| Daño cargador | Hardware | Estacion de trabajo | Computador | ALTA |
| Daño de microfono/audio | Hardware | Estacion de trabajo | Computador | MEDIA |
| Daño de teclado | Hardware | Estacion de trabajo | Computador | MEDIA |
| Daño display/pantalla | Hardware | Estacion de trabajo | Computador | ALTA |
| Equipo fuera del dominio | Hardware | Estacion de trabajo | Computador | MEDIA |
| Falla en cola de impresion | Hardware | Impresion | Impresora | MEDIA |
| Impresora no enciende | Hardware | Impresion | Impresora | MEDIA |
| No digitaliza | Hardware | Impresion | Impresora | BAJA |
| No llega archivo | Hardware | Impresion | Impresora | MEDIA |
| No saca copias | Hardware | Impresion | Impresora | MEDIA |
| Sin tinta | Hardware | Impresion | Impresora | MEDIA |
| Volcado de memoria | Hardware | Estacion de trabajo | Computador | MEDIA |

## Gestion de tickets

| Cat Op 2 | Cat Prod 1 | Cat Prod 2 | Cat Prod 3 | Prioridad |
|----------|-----------|-----------|-----------|-----------|
| Convertir a solicitud | Gestion de casos | Control | Casos | ALTA |

## Infraestructura

| Cat Op 2 | Cat Prod 1 | Cat Prod 2 | Cat Prod 3 | Prioridad |
|----------|-----------|-----------|-----------|-----------|
| Alto consumo de recursos | GTI | Administracion de aplicaciones | Plataforma | MEDIA |
| Alto consumo de recursos | GTI | Seguridad perimetral | Infraestructura | ALTA |
| Bloquear Sitio Web con Web Security | GTI | Seguridad perimetral | Infraestructura | MEDIA |
| Bloqueo de aplicacion | GTI | Antivirus | Plataforma | MEDIA |
| Caida de nodo | GTI | AWS | Infraestructura | ALTA |
| Caida del servicio | GTI | Redes | Infraestructura | CRITICA |
| Caida servidor | GTI | Administracion de aplicaciones | Plataforma | CRITICA |
| Canal saturado | GTI | Redes | Infraestructura | MEDIA |
| Certificado caducado | GTI | Redes | Infraestructura | ALTA |
| Cierre de vulnerabilidades | GTI | Backup | Plataforma | CRITICA |
| Cierre de vulnerabilidades | GTI | Base de datos | Plataforma | CRITICA |
| Cierre de vulnerabilidades | GTI | Seguridad perimetral | Infraestructura | CRITICA |
| Cierre de vulnerabilidades | GTI | Servidor microsoft | Plataforma | CRITICA |
| Cierre de vulnerabilidades | GTI | Virtualizacion | Plataforma | CRITICA |
| Cierre vulnerabilidades | GTI | Administracion de aplicaciones | Plataforma | CRITICA |
| Cierre vulnerabilidades | GTI | Redes | Infraestructura | CRITICA |
| Desbordamiento de memoria | GTI | Administracion de aplicaciones | Plataforma | MEDIA |
| Error al generar backup | GTI | Backup | Plataforma | ALTA |
| Error de enrutamiento | GTI | Seguridad perimetral | Infraestructura | MEDIA |
| Error de escritura | GTI | Servidor microsoft | Plataforma | MEDIA |
| Error de servidor | GTI | Administracion de aplicaciones | Plataforma | MEDIA |
| Evento de disponibilidad | GTI | AWS | Infraestructura | CRITICA |
| Evento de disponibilidad | GTI | Administracion de aplicaciones | Plataforma | CRITICA |
| Evento de disponibilidad | GTI | Backup | Plataforma | CRITICA |
| Evento de disponibilidad | GTI | Base de datos | Plataforma | CRITICA |
| Evento de disponibilidad | GTI | Redes | Infraestructura | CRITICA |
| Evento de disponibilidad | GTI | Seguridad perimetral | Infraestructura | CRITICA |
| Evento de disponibilidad | GTI | Servidor | Linux | CRITICA |
| Evento de disponibilidad | GTI | Servidor microsoft | Plataforma | CRITICA |
| Evento de disponibilidad | GTI | Virtualizacion | Plataforma | CRITICA |
| Falla aplicacion | GTI | Backup | Plataforma | ALTA |
| Falla de acceso a base de datos | GTI | Base de datos | Plataforma | ALTA |
| Falla de acceso carpeta de red | GTI | Servidor microsoft | Plataforma | MEDIA |
| Falla de conexion/navegacion red cableada | GTI | Redes | Infraestructura | CRITICA |
| Falla de conexion/navegacion red wifi | GTI | Redes | Infraestructura | ALTA |
| Falla de configuracion de servicios | GTI | Seguridad perimetral | Infraestructura | BAJA |
| Falla de libreria fisica/virtual | GTI | AWS | Infraestructura | ALTA |
| Falla de libreria fisica/virtual | GTI | Backup | Plataforma | ALTA |
| Falla de punto de red | GTI | Redes | Infraestructura | MEDIA |
| Falla de sistema operativo en servidor | GTI | AWS | Infraestructura | MEDIA |
| Falla de sistema operativo en servidor | GTI | Backup | Plataforma | ALTA |
| Falla en base de datos | GTI | Base de datos | Plataforma | ALTA |
| Falla sincronizacion nube | GTI | AWS | Infraestructura | MEDIA |
| Fallas de conexion ftp | GTI | Servidor microsoft | Plataforma | MEDIA |
| Fallas de conexion ftp linux | GTI | Servidor | Linux | MEDIA |
| Fallas por configuracion del servicio | GTI | Redes | Infraestructura | ALTA |
| Falta espacio en disco | GTI | Servidor microsoft | Plataforma | MEDIA |
| Incidente de seguridad | GTI | Base de datos | Plataforma | CRITICA |
| Incidente de seguridad | GTI | Servidor | Linux | CRITICA |
| Incidente de seguridad | GTI | Servidor microsoft | Plataforma | CRITICA |
| Incremento hilos de aplicacion | GTI | Administracion de aplicaciones | Plataforma | MEDIA |
| Indisponibilidad componente | GTI | AWS | Infraestructura | ALTA |
| Latencia | GTI | Servidor | Linux | BAJA |
| Latencia | GTI | Servidor microsoft | Plataforma | MEDIA |
| Lentitud en el servicio/caida de nodo | GTI | AWS | Infraestructura | ALTA |
| Lentitud en la aplicacion | GTI | Administracion de aplicaciones | Plataforma | BAJA |
| Lentitud en la aplicacion | GTI | Directorio activo | Plataforma | MEDIA |
| Lentitud en la navegacion red cableada | GTI | Redes | Infraestructura | MEDIA |
| Lentitud en la navegacion red wifi | GTI | Redes | Infraestructura | MEDIA |
| Reinicio por volcados por hilos | GTI | Administracion de aplicaciones | Plataforma | CRITICA |
| Tiempo de respuesta critico | GTI | Administracion de aplicaciones | Plataforma | MEDIA |
| Tiempo de respuesta critico | GTI | Administracion de aplicaciones | Plataforma | MEDIA |
