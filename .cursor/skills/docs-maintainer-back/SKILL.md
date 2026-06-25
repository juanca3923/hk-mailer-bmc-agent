---
name: docs-maintainer-back
description: >-
  Maintains project documentation aligned with code changes. Use when implementing
  features, fixes, refactors, API changes, deployment/config updates, or structure
  changes that affect README, architecture docs, changelog, or operational guides.
---

# Mantenedor de Documentación (Back)

## Objetivo

Mantener la documentación sincronizada con el estado real del proyecto, en el mismo flujo del cambio de código.

## Idioma de la documentación

La documentación debe escribirse preferiblemente en español.

Se permiten tecnicismos, keywords o términos sin traducción natural al español cuando hacerlo mejore claridad y precisión.

## Cuándo usar esta skill

Aplicar esta skill cuando el cambio afecte alguno de estos puntos:

- Comportamiento visible para usuarios o integradores.
- Contratos de API, eventos, entradas/salidas o formatos.
- Variables de entorno, despliegue o ejecución local.
- Estructura del repositorio (módulos, carpetas, componentes).
- Trazabilidad de producto (bugs, mejoras, funcionalidades nuevas o removidas).

## Qué documentar (mapa universal)

| Documento | Ruta sugerida | Qué debe reflejar |
|---|---|---|
| README | `README.md` | Cómo ejecutar, configurar, desplegar y operar el proyecto. |
| Arquitectura | `docs/ARCHITECTURE.md` | Componentes, flujos, límites, estructura y decisiones de diseño vigentes. |
| Changelog | `docs/CHANGELOG.md` | Registro cronológico de cambios relevantes con fecha y contexto. |
| Ejemplos operativos | `README.md` y/o `docs/` | Ejemplos de ejecución reales (CLI, Compose, requests, payloads). |

## Reglas de actualización

1. No dejar documentación para después si el cambio impacta operación o entendimiento.
2. Si hay cambio en despliegue Docker/Compose, incluir o actualizar ejemplo de `compose` sin secretos.
3. Si cambia API pública, la colección Postman es obligatoria: crearla si no existe y actualizarla si ya existe, siempre en el mismo flujo.
4. Si cambia estructura de carpetas o módulos, actualizar el mapa arquitectónico.
5. Si cambia configuración, reflejar defaults, obligatorias y valores de ejemplo seguros.

## Matriz de impacto para librerías e integraciones

No decidir por nombre de librería, sino por impacto funcional y operativo.

- Documentación obligatoria:
  - Cambios de contrato/API (incluye colección Postman obligatoria: crear o actualizar).
  - Integraciones o librerías que introducen operación nueva: migraciones, persistencia, mensajería, auth, observabilidad o despliegue.
- Documentación condicional:
  - Librerías que agregan comandos, variables de entorno, setup o troubleshooting.
- No requerido por defecto:
  - Librerías de implementación interna sin impacto en operación, contrato o arquitectura.

## Pregunta opcional al desarrollador

Si se implementa una librería/integración nueva, preguntar si desea documentación adicional específica (guía de uso, migración, troubleshooting, runbook).

Si la respuesta es sí, registrar el alcance y hacer seguimiento: cada cambio posterior en esa funcionalidad debe mantener esa documentación sincronizada.

## Flujo recomendado (checklist)

Usa esta lista y marca avance:

```text
Task Progress:
- [ ] 1) Detectar impacto documental del cambio
- [ ] 2) Actualizar README (run/config/deploy/ejemplos)
- [ ] 3) Actualizar ARCHITECTURE (estructura/flujos/componentes)
- [ ] 4) Actualizar CHANGELOG (fecha + qué + por qué importa)
- [ ] 5) Confirmar si requiere documentación adicional (solo si hay librerías/integraciones nuevas)
- [ ] 6) Validar consistencia entre código y docs
```

## Paso a paso

### 1) Detectar impacto

Preguntas de control:

- ¿Se modificó cómo correr el proyecto?
- ¿Se agregaron/editaron variables de entorno?
- ¿Se alteraron rutas, herramientas o contratos?
- ¿Se movieron archivos, paquetes o responsabilidades?

Si alguna respuesta es sí, actualiza documentos en el mismo cambio.

### 2) Actualizar README

Verificar y ajustar:

- Requisitos y comando de arranque.
- Variables de entorno requeridas/opcionales.
- Ejecución con Docker/Compose (incluyendo perfil dev si aplica).
- Ejemplos mínimos de uso.

### 3) Actualizar arquitectura

Reflejar:

- Nuevos componentes o eliminación de existentes.
- Cambios de flujo entre módulos o servicios.
- Reorganización de carpetas/paquetes.

### 4) Actualizar changelog

Agregar entrada con:

- Fecha.
- Tipo de cambio (`feat`, `fix`, `docs`, `refactor`, etc.).
- Descripción breve del impacto.

### 5) Confirmar documentación adicional (opcional)

Si se incorporan librerías/integraciones con impacto operativo, preguntar al desarrollador si quiere documentación adicional.

Si existe, mantenerla como parte obligatoria en cambios futuros de esa funcionalidad.

### 6) Validar consistencia final

Checklist de salida:

- Rutas mencionadas existen.
- Comandos documentados funcionan en el proyecto actual.
- Nombres de variables coinciden con el código.
- Ejemplos no contienen secretos reales.
- Si hubo cambios de API, existe colección Postman y está alineada al contrato actual.

## Criterios de calidad documental

- Ser concreto: qué cambió y por qué importa.
- Priorizar información operativa sobre texto narrativo largo.
- Mantener terminología consistente en todo el repo.
- Evitar duplicación innecesaria entre README y docs internos.

## Plantilla corta de actualización

```markdown
## [YYYY-MM-DD] Tipo: feat|fix|docs|refactor
- Cambio: <qué se cambió>
- Impacto: <a quién o qué afecta>
- Acción operativa: <qué debe hacer quien despliega/usa>
```
