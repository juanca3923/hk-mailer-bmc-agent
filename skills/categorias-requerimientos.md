---
name: categorias-requerimientos
description: Catálogo oficial de categorías BMC Helix ARUS para crear Work Orders (Requerimientos). Consulta siempre antes de llamar create_work_order.
---

# Categorías BMC Helix — Requerimiento (Work Order)

Usa esta guía para seleccionar la combinación **exacta** de campos de categorización
al crear un **Work Order** con `create_work_order`.

## Campos que debes completar

| Parámetro en `create_work_order` | Columna en esta guía |
|---------------------------------|---------------------|
| `categorization_tier_1` | Cat Op 1 |
| `categorization_tier_2` | Cat Op 2 |
| `categorization_tier_3` | dejar vacío `""` siempre |
| `product_cat_tier_1` | Cat Prod 1 |
| `product_cat_tier_2` | Cat Prod 2 |
| `product_cat_tier_3` | Cat Prod 3 |
| `priority` | usar el valor de la columna Prioridad en minúscula: `Medium`, `High`, `Low`, `Critical` |

### Mapeo Prioridad → priority

| Prioridad | Valor para `priority` |
|-----------|----------------------|
| CRITICA | `Critical` |
| ALTA | `High` |
| MEDIA | `Medium` |
| BAJA | `Low` |

> **Regla:** elige la fila que mejor describe el caso del usuario.
> Copia los valores **exactamente** como aparecen en la tabla.
> Cat Op 3 (`categorization_tier_3`) siempre va vacío `""`.

## Administrativos

| Cat Op 2 | Cat Prod 1 | Cat Prod 2 | Cat Prod 3 | Prioridad |
|----------|-----------|-----------|-----------|-----------|
| Asignar | Proceso de negocio | Tarjeta de acceso | Carne | ALTA |
| Cerrar codigo de proyecto | Proceso de negocio | Gestion | Financiera | BAJA |
| Ingreso personal buk | Proceso de negocio | Seleccion | Gestion laboral | BAJA |
| Realizar inventario | Proceso de negocio | Locativo | Inventario | ALTA |
| Renovacion | Proceso de negocio | Tarjeta de acceso | Carne | ALTA |
| Reposicion | Proceso de negocio | Tarjeta de acceso | Carne | ALTA |
| Retiro personal buk | Proceso de negocio | Seleccion | Gestion laboral | BAJA |

## Aplicacion

| Cat Op 2 | Cat Prod 1 | Cat Prod 2 | Cat Prod 3 | Prioridad |
|----------|-----------|-----------|-----------|-----------|
| Activar reporte de modulo | Software | Mosaico | Aplicacion | BAJO |
| Activar usuario | Software | Nemesis | Aplicacion | BAJA |
| Activar/inactivar usuario | Software | Herramienta de gestion | Aplicacion | BAJA |
| Actualizar lotes | Software | Datarus | Aplicacion | BAJA |
| Actualizar lotes | Software | Nemesis | Aplicacion | BAJA |
| Actualizar usuarios masivo | Software | Herramienta de gestion | Aplicacion | BAJA |
| Actualizar version | Software | Forticlient | Aplicacion | ALTA |
| Actualizar version | Software | Ligthshot | Aplicacion | BAJO |
| Actualizar version | Software | Software | Aplicacion | BAJO |
| Agregar/modificar lista blanca/negra | Software | Correo electronico | Aplicacion | MEDIO |
| Ajustar dashboard | Software | Gobierno de datos | Aplicacion | MEDIO |
| Ajustar umbral | Software | Consola de monitoreo | Aplicacion | MEDIO |
| Ajuste menor | Software | Buk | Aplicacion | ALTA |
| Ajuste menor | Software | RPA Compras | Aplicacion | ALTO |
| Ajuste menor | Software | RPA Contabilidad | Aplicacion | ALTO |
| Ajuste menor | Software | RPA Facturacion | Aplicacion | ALTO |
| Ajuste menor | Software | RPA accesos | Aplicacion | ALTO |
| Ajuste menor | Software | Sap | Aplicacion | ALTO |
| Ajuste reporte | Software | Sap | Aplicacion | BAJO |
| Ajuste reporte | Software | Vital E | Aplicacion | BAJO |
| Asesoria | Software | Auditoria de accesos | Aplicacion | BAJO |
| Asesoria | Software | Bisourcing | Aplicacion | BAJO |
| Asesoria | Software | Bizagi | Aplicacion | ALTA |
| Asesoria | Software | Bizagi bpm Compras | Aplicacion | ALTA |
| Asesoria | Software | Bizagi bpm Cotizadores | Aplicacion | ALTA |
| Asesoria | Software | Buk | Aplicacion | ALTA |
| Asesoria | Software | CMI Sura | Aplicacion | BAJO |
| Asesoria | Software | Consola de monitoreo | Aplicacion | BAJA |
| Asesoria | Software | Correo electronico | Aplicacion | ALTA |
| Asesoria | Software | Datarus | Aplicacion | BAJA |
| Asesoria | Software | Efi alfa | Aplicacion | ALTA |
| Asesoria | Software | Efi alinea2 | Aplicacion | ALTA |
| Asesoria | Software | Efi cuentas por pagar | Aplicacion | ALTA |
| Asesoria | Software | Efi dedicacion de horas y subrepartos | Aplicacion | ALTA |
| Asesoria | Software | Efi prefacturador | Aplicacion | ALTA |
| Asesoria | Software | Efi presupuesto | Aplicacion | ALTA |
| Asesoria | Software | Efi telefonia | Aplicacion | ALTA |
| Asesoria | Software | FE Cadena | Aplicacion | BAJO |
| Asesoria | Software | Forticlient | Aplicacion | ALTA |
| Asesoria | Software | Gestion de proveedores | Aplicacion | ALTA |
| Asesoria | Software | Gestiona tu acceso | Aplicacion | ALTA |
| Asesoria | Software | Herramienta de gestion | Aplicacion | BAJA |
| Asesoria | Software | Iris | Aplicacion | BAJO |
| Asesoria | Software | Jira | Aplicacion | BAJO |
| Asesoria | Software | Kiosko | Aplicacion | BAJO |
| Asesoria | Software | La U | Aplicacion | ALTA |
| Asesoria | Software | Ligthshot | Aplicacion | BAJO |
| Asesoria | Software | Mosaico | Aplicacion | BAJO |
| Asesoria | Software | Mosaico Administrativo Indicadores | Aplicacion | ALTA |
| Asesoria | Software | Mosaico Administrativo Registro Visitantes | Aplicacion | ALTA |
| Asesoria | Software | Nemesis | Aplicacion | BAJA |
| Asesoria | Software | Nomus | Aplicacion | ALTA |
| Asesoria | Software | Pentaho | Aplicacion | ALTA |
| Asesoria | Software | Prisma | Aplicacion | BAJA |
| Asesoria | Software | Prometeo | Aplicacion | CRITICO |
| Asesoria | Software | RPA Compras | Aplicacion | BAJO |
| Asesoria | Software | RPA Contabilidad | Aplicacion | BAJO |
| Asesoria | Software | RPA Facturacion | Aplicacion | BAJO |
| Asesoria | Software | RPA accesos | Aplicacion | BAJO |
| Asesoria | Software | Rips | Aplicacion | BAJO |
| Asesoria | Software | Salesforce | Aplicacion | ALTA |
| Asesoria | Software | Sap | Aplicacion | BAJO |
| Asesoria | Software | Software | Aplicacion | ALTO |
| Asesoria | Software | Teams | Aplicacion | ALTA |
| Asesoria | Software | Telefonia administrativa | Aplicacion | MEDIO |
| Asesoria | Software | Tienda ARUS | Aplicacion | ALTA |
| Asesoria | Software | Vital E | Aplicacion | ALTA |
| Asignacion pin de llamadas | Software | Telefonia administrativa | Aplicacion | BAJO |
| Asignar extension | Software | Telefonia administrativa | Aplicacion | BAJO |
| Asignar permisos | Software | Auditoria de accesos | Aplicacion | ALTO |
| Asignar permisos | Software | Bisourcing | Aplicacion | ALTA |
| Asignar permisos | Software | Bizagi bpm Cotizadores | Aplicacion | ALTA |
| Asignar permisos | Software | CMI Sura | Aplicacion | ALTA |
| Asignar permisos | Software | Efi activos | Aplicacion | ALTA |
| Asignar permisos | Software | Efi alfa | Aplicacion | MEDIO |
| Asignar permisos | Software | Efi alinea2 | Aplicacion | MEDIO |
| Asignar permisos | Software | Efi cuentas por pagar | Aplicacion | MEDIO |
| Asignar permisos | Software | Efi dedicacion de horas y subrepartos | Aplicacion | MEDIO |
| Asignar permisos | Software | Efi prefacturador | Aplicacion | MEDIO |
| Asignar permisos | Software | Efi presupuesto | Aplicacion | MEDIO |
| Asignar permisos | Software | Efi telefonia | Aplicacion | MEDIO |
| Asignar permisos | Software | Gestion de proveedores | Aplicacion | BAJO |
| Asignar permisos | Software | Iris | Aplicacion | ALTA |
| Asignar permisos | Software | Jira | Aplicacion | ALTA |
| Asignar permisos | Software | La U | Aplicacion | BAJO |
| Asignar permisos | Software | Mosaico Administrativo Indicadores | Aplicacion | BAJO |
| Asignar permisos | Software | Mosaico Administrativo Registro Visitantes | Aplicacion | BAJO |
| Asignar permisos | Software | Nemesis | Aplicacion | BAJA |
| Asignar permisos | Software | Nomus | Aplicacion | BAJO |
| Asignar permisos | Software | Pentaho | Aplicacion | BAJO |
| Asignar permisos | Software | Salesforce | Aplicacion | BAJO |
| Asignar permisos | Software | Tienda ARUS | Aplicacion | BAJO |
| Asignar token | Software | Forticlient | Aplicacion | ALTA |
| Asignar transacciones | Software | Sap | Aplicacion | BAJO |
| Asignar/modificar licencia | Software | Office 365 | Aplicacion | MEDIO |
| Asignar/modificar licencia | Software | Software | Aplicacion | BAJO |
| Asignar/modificar rol | Software | Prisma | Aplicacion | BAJA |
| Asignar/retirar permiso de grabacion | Software | Teams | Aplicacion | MEDIO |
| Borrar informacion de BD | Software | Vital E | Aplicacion | BAJO |
| Cambiar contraseña | Software | Prisma | Aplicacion | BAJA |
| Cambiar contraseña | Software | Telefonia especializada | Aplicacion | MEDIO |
| Cambiar contraseña  | Software | Vital E | Aplicacion | ALTA |
| Cambiar estado de lotes | Software | Datarus | Aplicacion | BAJA |
| Cambiar estado de lotes | Software | Nemesis | Aplicacion | BAJA |
| Cambiar nombre de cuenta | Software | Correo electronico | Aplicacion | MEDIO |
| Cambiar nombre de extension | Software | Telefonia especializada | Aplicacion | BAJO |
| Cambio de nombre de extension | Software | Telefonia administrativa | Aplicacion | BAJO |
| Compartir archivos | Software | One drive | Aplicacion | MEDIO |
| Configurar | Software | Datarus | Aplicacion | BAJA |
| Configurar aplicacion | Software | Software | Aplicacion | BAJO |
| Configurar extension | Software | Telefonia administrativa | Aplicacion | BAJO |
| Configurar maestras | Software | Efi activos | Aplicacion | MEDIO |
| Configurar maestras | Software | Efi alfa | Aplicacion | ALTA |
| Configurar maestras | Software | Efi alinea2 | Aplicacion | ALTA |
| Configurar maestras | Software | Efi cuentas por pagar | Aplicacion | ALTA |
| Configurar maestras | Software | Efi dedicacion de horas y subrepartos | Aplicacion | ALTA |
| Configurar maestras | Software | Efi prefacturador | Aplicacion | ALTA |
| Configurar maestras | Software | Efi presupuesto | Aplicacion | ALTA |
| Configurar maestras | Software | Efi telefonia | Aplicacion | ALTA |
| Configurar token | Software | Office 365 | Aplicacion | ALTA |
| Configurar vpn | Software | Forticlient | Aplicacion | ALTA |
| Crear alias | Software | Correo electronico | Aplicacion | MEDIO |
| Crear bandeja | Software | Nemesis | Aplicacion | BAJA |
| Crear campos personalizados | Software | Herramienta de gestion | Aplicacion | BAJA |
| Crear de cuenta  | Software | Buk | Aplicacion | ALTA |
| Crear nuevo dashboard | Software | Gobierno de datos | Aplicacion | MEDIO |
| Crear permisos/autorizaciones | Software | Sap | Aplicacion | BAJO |
| Crear reglas de enrutamiento | Software | Datarus | Aplicacion | BAJA |
| Crear usuario | Software | Mosaico | Aplicacion | MEDIO |
| Crear/cambiar contraseña | Software | Gestiona tu acceso | Aplicacion | ALTA |
| Crear/cambiar contraseña | Software | Sap | Aplicacion | BAJO |
| Crear/eliminar/modificar grupos de distribucion | Software | Correo electronico | Aplicacion | MEDIO |
| Crear/modificar clave de acceso | Software | Herramienta de gestion | Aplicacion | BAJA |
| Crear/modificar/ eliminar usuario | Software | Herramienta de gestion | Aplicacion | BAJA |
| Crear/modificar/eliminar cuenta generica | Software | Correo electronico | Aplicacion | MEDIO |
| Crear/modificar/eliminar cuenta/licencia | Software | Correo electronico | Aplicacion | MEDIO |
| Crear/modificar/eliminar reporte avanzado | Software | Herramienta de gestion | Aplicacion | BAJA |
| Crear/modificar/eliminar usuario | Software | Datarus | Aplicacion | MEDIA |
| Crear/modificar/eliminar usuario | Software | Nemesis | Aplicacion | BAJA |
| Crear/modificar/eliminar usuario | Software | Prisma | Aplicacion | BAJA |
| Crear/modificar/eliminar usuario en consola | Software | Consola de monitoreo | Aplicacion | BAJO |
| Crear/modificar/eliminar/activar/inactivar/desbloquear usuario | Software | Bizagi bpm Compras | Aplicacion | ALTA |
| Crear/modificar/eliminar/activar/inactivar/desbloquear usuario | Software | Gestiona tu acceso | Aplicacion | ALTA |
| Crear/modificar/eliminar/activar/inactivar/desbloquear usuario | Software | Sap | Aplicacion | BAJO |
| Crear/modificar/eliminar/revisar ci | Software | Consola de monitoreo | Aplicacion | BAJO |
| Crear/modificar/inactivar ans | Software | Herramienta de gestion | Aplicacion | BAJA |
| Crear/modificar/inactivar categoria | Software | Herramienta de gestion | Aplicacion | BAJA |
| Crear/modificar/inactivar grupo | Software | Herramienta de gestion | Aplicacion | BAJA |
| Crear/modificar/inactivar oferta de catalogo | Software | Herramienta de gestion | Aplicacion | BAJA |
| Crear/modificar/inactivar usuario | Software | Bisourcing | Aplicacion | ALTA |
| Crear/modificar/inactivar usuario | Software | Bizagi bpm Cotizadores | Aplicacion | BAJO |
| Delegar buzon | Software | Correo electronico | Aplicacion | MEDIO |
| Desbloqueo de cuenta | Software | Sap | Aplicacion | BAJO |
| Ejecutar query | Software | Nemesis | Aplicacion | BAJA |
| Estimar necesidad | Software | Datarus | Aplicacion | BAJA |
| Evento de capacidad | Software | Telefonia especializada | Aplicacion | CRITICO |
| Generar acceso | Software | Mosaico | Aplicacion | BAJO |
| Generar grabacion de llamadas | Software | Telefonia administrativa | Aplicacion | BAJO |
| Generar reporte | Software | Consola de monitoreo | Aplicacion | BAJO |
| Generar reporte | Software | Herramienta de gestion | Aplicacion | BAJA |
| Generar reporte | Software | Mosaico | Aplicacion | BAJO |
| Generar reporte de llamadas | Software | Telefonia administrativa | Aplicacion | BAJO |
| Generar transporte de ordenes | Software | Sap | Aplicacion | BAJO |
| Gestionar capacidad | Software | Correo electronico | Aplicacion | MEDIO |
| Informacion de la aplicacion | Software | Herramienta de gestion | Aplicacion | BAJA |
| Instalar | Software | Bizagi | Aplicacion | ALTA |
| Instalar agente MFA | Software | Gestiona tu acceso | Aplicacion | MEDIO |
| Instalar agente MFA | Software | Prometeo | Aplicacion | MEDIO |
| Instalar aplicacion | Software | Ligthshot | Aplicacion | BAJO |
| Instalar aplicacion | Software | Office 365 | Aplicacion | ALTA |
| Instalar aplicacion | Software | Sap | Aplicacion | BAJO |
| Instalar aplicacion | Software | Software | Aplicacion | BAJO |
| Liberar ordenes de transporte | Software | Sap | Aplicacion | BAJO |
| Modificar bandeja | Software | Nemesis | Aplicacion | BAJA |
| Modificar categorizacion con ans | Software | Herramienta de gestion | Aplicacion | BAJA |
| Modificar contraseña | Software | Nemesis | Aplicacion | BAJA |
| Modificar informacion de BD | Software | Vital E | Aplicacion | BAJO |
| Modificar parametros de notificacion | Software | Mosaico | Aplicacion | BAJO |
| Modificar parametros de notificacion  | Software | Herramienta de gestion | Aplicacion | BAJA |
| Modificar permiso a modulo | Software | Mosaico | Aplicacion | BAJO |
| Modificar recursos en el calendario | Software | Correo electronico | Aplicacion | MEDIO |
| Modificar regla de enrutamiento | Software | Nemesis | Aplicacion | BAJA |
| Modificar rol | Software | Efi activos | Aplicacion | ALTA |
| Modificar rol | Software | Efi alfa | Aplicacion | BAJO |
| Modificar rol | Software | Efi alinea2 | Aplicacion | BAJO |
| Modificar rol | Software | Efi cuentas por pagar | Aplicacion | BAJO |
| Modificar rol | Software | Efi dedicacion de horas y subrepartos | Aplicacion | BAJO |
| Modificar rol | Software | Efi prefacturador | Aplicacion | BAJO |
| Modificar rol | Software | Efi presupuesto | Aplicacion | BAJO |
| Modificar rol | Software | Efi telefonia | Aplicacion | BAJO |
| Realizar backup | Software | Correo electronico | Aplicacion | MEDIO |
| Realizar backup | Software | One drive | Aplicacion | MEDIO |
| Retirar correo de cuarentena | Software | Correo electronico | Aplicacion | MEDIO |
| Revisar afiliacion eps sura | Software | Nemesis | Aplicacion | BAJA |
| Solicitud | Software | Mosaico | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Auditoria de accesos | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Bisourcing | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Bizagi bpm Compras | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Bizagi bpm Cotizadores | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Buk | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Efi activos | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Efi alfa | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Efi alinea2 | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Efi cuentas por pagar | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Efi dedicacion de horas y subrepartos | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Efi prefacturador | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Efi presupuesto | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Efi telefonia | Aplicacion | BAJO |
| Solicitud de estimacion | Software | RPA Compras | Aplicacion | BAJO |
| Solicitud de estimacion | Software | RPA Contabilidad | Aplicacion | BAJO |
| Solicitud de estimacion | Software | RPA Facturacion | Aplicacion | BAJO |
| Solicitud de estimacion | Software | RPA accesos | Aplicacion | BAJO |
| Solicitud de estimacion | Software | Sap | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Auditoria de accesos | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Bisourcing | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Bizagi bpm Compras | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Bizagi bpm Cotizadores | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Buk | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Efi activos | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Efi alfa | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Efi alinea2 | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Efi cuentas por pagar | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Efi dedicacion de horas y subrepartos | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Efi prefacturador | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Efi presupuesto | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Efi telefonia | Aplicacion | BAJO |
| Solicitud de implementacion | Software | RPA Compras | Aplicacion | BAJO |
| Solicitud de implementacion | Software | RPA Contabilidad | Aplicacion | BAJO |
| Solicitud de implementacion | Software | RPA Facturacion | Aplicacion | BAJO |
| Solicitud de implementacion | Software | RPA accesos | Aplicacion | BAJO |
| Solicitud de implementacion | Software | Sap | Aplicacion | BAJO |
| Solicitud de informe | Software | Bisourcing | Aplicacion | BAJO |
| Solicitud de informe | Software | Sap | Aplicacion | BAJO |
| Solicitud de reportes | Software | Efi activos | Aplicacion | BAJO |
| Solicitud de reportes | Software | Efi alfa | Aplicacion | BAJO |
| Solicitud de reportes | Software | Efi alinea2 | Aplicacion | BAJO |
| Solicitud de reportes | Software | Efi cuentas por pagar | Aplicacion | BAJO |
| Solicitud de reportes | Software | Efi dedicacion de horas y subrepartos | Aplicacion | BAJO |
| Solicitud de reportes | Software | Efi prefacturador | Aplicacion | BAJO |
| Solicitud de reportes | Software | Efi presupuesto | Aplicacion | BAJO |
| Solicitud de reportes | Software | Efi telefonia | Aplicacion | BAJO |
| Solicitud de reportes | Software | Prisma | Aplicacion | BAJA |
| Validar/agregar/retirar personal a cargo | Software | Mosaico | Aplicacion | MEDIO |
| Verificar integridad de activos | Software | Efi activos | Aplicacion | BAJO |
| Verificar integridad de informacion | Software | Efi activos | Aplicacion | BAJO |
| Verificar integridad de informacion | Software | Efi alfa | Aplicacion | BAJO |
| Verificar integridad de informacion | Software | Efi cuentas por pagar | Aplicacion | BAJO |
| Verificar integridad de informacion | Software | Efi dedicacion de horas y subrepartos | Aplicacion | BAJO |
| Verificar integridad de informacion | Software | Efi prefacturador | Aplicacion | BAJO |
| Verificar integridad de informacion | Software | Efi presupuesto | Aplicacion | BAJO |
| Verificar integridad de informacion | Software | Efi telefonia | Aplicacion | BAJO |

## Equipos Tecnologicos

| Cat Op 2 | Cat Prod 1 | Cat Prod 2 | Cat Prod 3 | Prioridad |
|----------|-----------|-----------|-----------|-----------|
| Actualizar sistema operativo /controladores/certificado seguridad | Hardware | Estacion de trabajo | Computador | MEDIO |
| Aprobar uso del software | Hardware | Estacion de trabajo | Computador | BAJA |
| Asesoria | Hardware | Estacion de trabajo | Computador | ALTA |
| Asignar accesorios/perifericos | Hardware | Estacion de trabajo | Computador | MEDIO |
| Asignar activo | Hardware | Estacion de trabajo | Computador | ALTA |
| Asignar licencia de software | Hardware | Estacion de trabajo | Computador | BAJO |
| Asignar pin | Hardware | Impresion | Impresora | ALTA |
| Comprar activo | Hardware | Estacion de trabajo | Computador | BAJA |
| Configurar | Hardware | Impresion | Impresora | MEDIO |
| Configurar BitLocker/absolute | Hardware | Estacion de trabajo | Computador | ALTA |
| Configurar huella | Hardware | Estacion de trabajo | Computador | MEDIO |
| Cotizar activo | Hardware | Estacion de trabajo | Computador | BAJO |
| Diagnosticar equipo | Hardware | Estacion de trabajo | Computador | MEDIO |
| Diagnosticar equipo | Hardware | Impresion | Impresora | MEDIO |
| Formatear equipo | Hardware | Estacion de trabajo | Computador | ALTA |
| Gestionar garantia | Hardware | Estacion de trabajo | Computador | MEDIO |
| Gestionar garantia | Hardware | Impresion | Impresora | MEDIO |
| Gestionar permisos de impresion | Hardware | Impresion | Impresora | MEDIO |
| Instalar | Hardware | Impresion | Impresora | MEDIO |
| Mantenimiento preventivo | Hardware | Estacion de trabajo | Computador | MEDIO |
| Reportar Perdida/ hurto equipo | Hardware | Estacion de trabajo | Computador | ALTA |
| Retiro de activo | Hardware | Estacion de trabajo | Computador | ALTA |
| Verificar datos del usuario | Hardware | Impresion | Impresora | MEDIO |

## Gestion de tickets

| Cat Op 2 | Cat Prod 1 | Cat Prod 2 | Cat Prod 3 | Prioridad |
|----------|-----------|-----------|-----------|-----------|
| Acompañamiento | Gestion de casos | Control | Casos | CRITICO |
| Convertir a Incidente | Gestion de casos | Control | Casos | CRITICO |
| Informacion estado del caso | Gestion de casos | Control | Casos | CRITICO |
| Llamada equivocada | Gestion de casos | Control | Casos | CRITICO |
| Llamada informativa | Gestion de casos | Control | Casos | CRITICO |
| Ticket cancelado | Gestion de casos | Control | Casos | CRITICO |
| Ticket de prueba | Gestion de casos | Control | Casos | CRITICO |

## Infraestructura

| Cat Op 2 | Cat Prod 1 | Cat Prod 2 | Cat Prod 3 | Prioridad |
|----------|-----------|-----------|-----------|-----------|
| Acceso/bloqueo  | GTI | Antivirus | Plataforma | MEDIO |
| Accesos ftp | GTI | Servidor microsoft | Plataforma | BAJA |
| Acompañamiento | GTI | Redes | Infraestructura | BAJO |
| Acompañamiento | GTI | Servidor | Linux | BAJO |
| Acompañamiento | GTI | Servidor microsoft | Plataforma | BAJO |
| Activar/desactivar firma en fortiweb | GTI | Seguridad perimetral | Infraestructura | BAJO |
| Agregar/modificar host | GTI | Redes | Infraestructura | MEDIO |
| Agregar/modificar sensor en prtg | GTI | Redes | Infraestructura | BAJO |
| Analisis de comportamiento | GTI | Administracion de aplicaciones | Plataforma | BAJO |
| Aplicar excepcion de firma ips | GTI | Seguridad perimetral | Infraestructura | MEDIO |
| Aplicar/generar certificado de seguridad | GTI | Administracion de aplicaciones | Plataforma | MEDIO |
| Asesoria | GTI | AWS | Infraestructura | BAJA |
| Asesoria | GTI | Antivirus | Plataforma | ALTA |
| Asesoria | GTI | Backup | Plataforma | BAJA |
| Asesoria | GTI | Redes | Infraestructura | BAJA |
| Asesoria | GTI | Seguridad perimetral | Infraestructura | BAJA |
| Asignar permisos de administrador | GTI | Directorio activo | Plataforma | BAJO |
| Asignar permisos en directorios | GTI | Administracion de aplicaciones | Plataforma | BAJA |
| Asignar permisos en servidor | GTI | Base de datos | Plataforma | BAJO |
| Asignar recursos | GTI | AWS | Infraestructura | BAJA |
| Asignar recursos | GTI | Servidor microsoft | Plataforma | BAJO |
| Asignar/modificar/eliminar permisos en carpeta de red | GTI | Servidor microsoft | Plataforma | MEDIO |
| Asignar/modificar/eliminar permisos en servidor | GTI | Servidor | Linux | BAJO |
| Asignar/modificar/eliminar permisos en servidor | GTI | Servidor microsoft | Plataforma | MEDIO |
| Asignar/modificar/eliminar privilegios | GTI | Base de datos | Plataforma | BAJO |
| Asignar/modificar/eliminar recursos | GTI | Servidor | Linux | BAJO |
| Asignar/retirar/inactivar permisos | GTI | AWS | Infraestructura | BAJA |
| Asignar/retirar/inactivar roles | GTI | AWS | Infraestructura | BAJA |
| Aumentar capacidad | GTI | Administracion de aplicaciones | Plataforma | BAJA |
| Aumentar capacidad | GTI | Servidor microsoft | Plataforma | BAJO |
| Aumentar capacidad carpeta de red | GTI | Servidor microsoft | Plataforma | BAJO |
| Bloquear Sitio Web | GTI | Antivirus | Plataforma | ALTA |
| Bloquear dominio | GTI | Servidor microsoft | Plataforma | MEDIO |
| Cambiar arquitectura | GTI | Seguridad perimetral | Infraestructura | BAJO |
| Cambiar contraseña | GTI | AWS | Infraestructura | BAJA |
| Cambiar contraseña ftp | GTI | Servidor | Linux | BAJO |
| Cambio en infraestructura | GTI | Seguridad perimetral | Infraestructura | BAJO |
| Configurar grupo de Navegacion | GTI | Redes | Infraestructura | MEDIO |
| Configurar punto de red | GTI | Redes | Infraestructura | MEDIO |
| Configurar red cableada | GTI | Redes | Infraestructura | MEDIO |
| Configurar red wifi | GTI | Redes | Infraestructura | MEDIO |
| Configurar relay | GTI | Servidor | Linux | BAJO |
| Configurar servicios | GTI | AWS | Infraestructura | BAJA |
| Control de acceso a la red | GTI | Seguridad perimetral | Infraestructura | BAJO |
| Crear enrutamiento | GTI | Redes | Infraestructura | BAJA |
| Crear instancia | GTI | AWS | Infraestructura | BAJA |
| Crear regla de firewall denegacion | GTI | Seguridad perimetral | Infraestructura | MEDIO |
| Crear vlan | GTI | Redes | Infraestructura | BAJA |
| Crear/configurar host virtual/site | GTI | Administracion de aplicaciones | Plataforma | BAJA |
| Crear/instalar instancia estandar/atipica | GTI | Administracion de aplicaciones | Plataforma | ALTA |
| Crear/migrar sitios | GTI | Administracion de aplicaciones | Plataforma | BAJA |
| Crear/modificar politica de backups | GTI | Backup | Plataforma | BAJA |
| Crear/modificar/eliminar backup | GTI | Backup | Plataforma | BAJA |
| Crear/modificar/eliminar base de datos | GTI | Base de datos | Plataforma | BAJO |
| Crear/modificar/eliminar carpeta de red | GTI | Servidor microsoft | Plataforma | MEDIO |
| Crear/modificar/eliminar carpetas ftp | GTI | Servidor | Linux | BAJO |
| Crear/modificar/eliminar configuracion | GTI | Base de datos | Plataforma | BAJO |
| Crear/modificar/eliminar perfil fortidos | GTI | Seguridad perimetral | Infraestructura | BAJO |
| Crear/modificar/eliminar perfil fortiweb | GTI | Seguridad perimetral | Infraestructura | BAJO |
| Crear/modificar/eliminar permisos en vpn | GTI | Seguridad perimetral | Infraestructura | MEDIO |
| Crear/modificar/eliminar regla | GTI | Seguridad perimetral | Infraestructura | MEDIO |
| Crear/modificar/eliminar regla de firewall acceso | GTI | Seguridad perimetral | Infraestructura | BAJO |
| Crear/modificar/eliminar rol | GTI | Base de datos | Plataforma | BAJO |
| Crear/modificar/eliminar sitios | GTI | Servidor | Linux | BAJO |
| Crear/modificar/eliminar usuario | GTI | AWS | Infraestructura | BAJA |
| Crear/modificar/eliminar usuario | GTI | Base de datos | Plataforma | BAJO |
| Crear/modificar/eliminar usuario externo | GTI | Directorio activo | Plataforma | BAJO |
| Crear/modificar/eliminar/revisar ci de consola | GTI | Backup | Plataforma | BAJA |
| Crear/modificar/eliminar/suspender usuario | GTI | Servidor microsoft | Plataforma | ALTA |
| Crear/modificar/inactivar usuario administrador local | GTI | Directorio activo | Plataforma | BAJO |
| Crear/modificar/revisar job | GTI | Base de datos | Plataforma | BAJO |
| Depurar unidad de almacenamiento | GTI | Administracion de aplicaciones | Plataforma | MEDIO |
| Despliegue de artefacto | GTI | Administracion de aplicaciones | Plataforma | BAJA |
| Ejecutar scripts | GTI | Base de datos | Plataforma | BAJO |
| Escanear a demanda | GTI | Antivirus | Plataforma | BAJO |
| Evento de capacidad | GTI | AWS | Infraestructura | BAJA |
| Evento de capacidad | GTI | Administracion de aplicaciones | Plataforma | CRITICO |
| Evento de capacidad | GTI | Backup | Plataforma | CRITICO |
| Evento de capacidad | GTI | Base de datos | Plataforma | CRITICO |
| Evento de capacidad | GTI | Redes | Infraestructura | CRITICO |
| Evento de capacidad | GTI | Seguridad perimetral | Infraestructura | CRITICO |
| Evento de capacidad | GTI | Servidor | Linux | CRITICO |
| Evento de capacidad | GTI | Servidor microsoft | Plataforma | CRITICO |
| Excepcion en firma de seguridad fortiweb | GTI | Seguridad perimetral | Infraestructura | BAJO |
| Exclusion de inspeccion de trafico | GTI | Seguridad perimetral | Infraestructura | MEDIO |
| Generar acceso a base de datos | GTI | Base de datos | Plataforma | BAJO |
| Generar acceso a reportes | GTI | Base de datos | Plataforma | BAJO |
| Generar accesos ftp | GTI | Servidor | Linux | BAJO |
| Generar backup de base de datos | GTI | Backup | Plataforma | BAJA |
| Generar informe | GTI | Base de datos | Plataforma | BAJO |
| Generar reporte | GTI | Administracion de aplicaciones | Plataforma | BAJO |
| Generar reporte | GTI | Antivirus | Plataforma | BAJA |
| Generar reporte de navegacion | GTI | Redes | Infraestructura | BAJO |
| Generar reportes | GTI | Servidor microsoft | Plataforma | BAJO |
| Generar solicitud de reportes | GTI | Servidor | Linux | BAJO |
| Habilitar conexion red wifi | GTI | Redes | Infraestructura | MEDIO |
| Habilitar/bloquear puerto usb | GTI | Antivirus | Plataforma | BAJA |
| Habilitar/deshabilitar base de datos | GTI | Base de datos | Plataforma | BAJO |
| Implementar vpn sitio a sitio | GTI | Seguridad perimetral | Infraestructura | BAJO |
| Incluir sitio web en lista negra/blanca | GTI | Redes | Infraestructura | BAJA |
| Iniciar/detener componentes | GTI | Base de datos | Plataforma | BAJO |
| Instalar | GTI | Antivirus | Plataforma | ALTA |
| Instalar agente | GTI | Antivirus | Plataforma | ALTA |
| Instalar certificado de seguridad | GTI | Administracion de aplicaciones | Plataforma | MEDIO |
| Instalar/configurar/reiniciar componentes | GTI | Servidor | Linux | BAJO |
| Instalar/configurar/reiniciar servidor | GTI | Servidor | Linux | BAJO |
| Instalar/desinstalar motor de base de datos | GTI | Base de datos | Plataforma | BAJO |
| Modificar base de datos | GTI | AWS | Infraestructura | BAJA |
| Modificar configuracion de ips | GTI | Seguridad perimetral | Infraestructura | MEDIO |
| Modificar configuracion general firewall | GTI | Seguridad perimetral | Infraestructura | MEDIO |
| Modificar grupos directorio activo | GTI | Servidor microsoft | Plataforma | MEDIO |
| Mover maquina virtual | GTI | Virtualizacion | Plataforma | BAJO |
| Optimizar perfil fortiweb | GTI | Seguridad perimetral | Infraestructura | BAJO |
| Permiso de navegacion usuario | GTI | Redes | Infraestructura | MEDIO |
| Permiso en vpn cliente a sitio | GTI | Redes | Infraestructura | MEDIO |
| Publicar/modificar ruta en firewall | GTI | Seguridad perimetral | Infraestructura | MEDIO |
| Publicar/modificar/eliminar aplicacion por fortiweb | GTI | Seguridad perimetral | Infraestructura | BAJO |
| Realizar actualizacion | GTI | Virtualizacion | Plataforma | BAJO |
| Realizar mantenimiento | GTI | Administracion de aplicaciones | Plataforma | BAJO |
| Realizar snaphot | GTI | Virtualizacion | Plataforma | BAJO |
| Recategorizar sitio web | GTI | Redes | Infraestructura | MEDIO |
| Registrar dns | GTI | Servidor microsoft | Plataforma | BAJO |
| Reiniciar componentes | GTI | Administracion de aplicaciones | Plataforma | ALTA |
| Reiniciar componentes | GTI | Virtualizacion | Plataforma | BAJO |
| Reiniciar componentes servidor | GTI | Servidor microsoft | Plataforma | MEDIO |
| Renovar certificado aplicacion fortiweb | GTI | Seguridad perimetral | Infraestructura | BAJO |
| Reporte de consola | GTI | Backup | Plataforma | BAJA |
| Request de certificado | GTI | Servidor | Linux | BAJO |
| Request de certificado | GTI | Servidor microsoft | Plataforma | ALTA |
| Reservar direccion ip | GTI | Servidor microsoft | Plataforma | BAJO |
| Restaurar informacion desde backup | GTI | Backup | Plataforma | ALTA |
| Restaurar informacion desde base de datos | GTI | Backup | Plataforma | ALTA |
| Revisar ap | GTI | Seguridad perimetral | Infraestructura | MEDIO |
| Revisar servidor | GTI | Servidor microsoft | Plataforma | BAJO |
| revisar servidor | GTI | Servidor | Linux | BAJO |

## PQRS

| Cat Op 2 | Cat Prod 1 | Cat Prod 2 | Cat Prod 3 | Prioridad |
|----------|-----------|-----------|-----------|-----------|
| Actitud de servicio | Calidad | Felicitacion | PQRSF | BAJA |
| Gestion soporte/analista | Calidad | Felicitacion | PQRSF | BAJA |
| Inconformidad con la actitud del soporte/analista | Calidad | Queja | PQRSF | BAJA |
| Inconformidad con la solucion | Calidad | Queja | PQRSF | BAJA |
| Inconformidad servicio | Calidad | Queja | PQRSF | BAJA |
| Inconformidad tiempos de atencion | Calidad | Queja | PQRSF | BAJA |
| Inconformidad tiempos de solucion | Calidad | Queja | PQRSF | BAJA |
| Por el servicio en general | Calidad | Felicitacion | PQRSF | BAJA |
| Por el servicio en general | Calidad | Sugerencia | PQRSF | BAJA |
| Por tiempos de respuesta | Calidad | Sugerencia | PQRSF | BAJA |
| Por tiempos de solucion | Calidad | Sugerencia | PQRSF | BAJA |
| Tiempos de respuesta acordes | Calidad | Felicitacion | PQRSF | BAJA |
| Tiempos de solucion acordes | Calidad | Felicitacion | PQRSF | BAJA |
