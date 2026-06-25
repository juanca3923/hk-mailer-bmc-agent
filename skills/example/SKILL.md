---
name: example
description: Skill de ejemplo versionada en el repositorio; sirve como plantilla para crear skills locales en skills/nombre-de-skill/SKILL.md.
---

# Skill de ejemplo (AgentForge)

Esta skill demuestra el formato Agent Skills que consume el arnés DeepAgents (la especificación completa es documentación humana en agentskills.io; no hace falta abrirla para usar esta plantilla).

## Cuándo usar esta skill

- Como referencia al crear nuevas carpetas `skills/<nombre>/SKILL.md`.
- El campo `name` del frontmatter debe coincidir exactamente con el nombre del directorio padre (`example`).

## Pasos sugeridos al crear una skill real

1. Copia esta carpeta y renómbrala (p. ej. `crear-correo`).
2. Ajusta `name` y `description` en el frontmatter (la descripción ayuda al modelo a decidir cuándo aplicar la skill).
3. Sustituye el cuerpo por tu procedimiento operativo.
