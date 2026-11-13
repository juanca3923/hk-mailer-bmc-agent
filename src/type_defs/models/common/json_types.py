"""Alias de tipos para estructuras JSON arbitrarias.

Usar JsonDict en lugar de dict[str, Any] para datos cuya estructura no es
conocida en tiempo de compilación (columnas JSONB, payloads de eventos, etc.).
El tipo resultante es más estricto: los valores se leen como `object` y
requieren isinstance() o cast() para usarlos, en vez de silenciar el type-checker.
"""

from __future__ import annotations

# Tipo para dicts JSON de estructura arbitraria (p. ej. JSONB, payloads de eventos).
JsonDict = dict[str, object]
