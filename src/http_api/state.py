"""Estado compartido del agente (uso en servicio HTTP)."""

from __future__ import annotations

from type_defs import StatusAgent


class AgentState:
    """Estado compartido del agente (uso en servicio HTTP)."""

    def __init__(self) -> None:
        self._status: StatusAgent = "DOWN"
        self._shutdown_requested = False

    @property
    def status(self) -> StatusAgent:
        """Obtener el estado actual del agente."""
        return self._status

    def set_status(self, value: StatusAgent) -> None:
        """Establecer el estado actual del agente."""
        self._status = value

    @property
    def shutdown_requested(self) -> bool:
        """Verificar si se ha solicitado la parada del agente."""
        return self._shutdown_requested

    def request_shutdown(self) -> None:
        """Solicitar la parada del agente."""
        self._shutdown_requested = True

    def clear_shutdown_requested(self) -> None:
        """Limpiar la solicitud de parada (p. ej. al volver a iniciar)."""
        self._shutdown_requested = False


agent_state = AgentState()
