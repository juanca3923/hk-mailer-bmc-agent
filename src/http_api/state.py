"""Estado compartido del agente (uso en servicio HTTP).

Por defecto (``allow_concurrent_turns=True``, ver ``HTTP_ALLOW_CONCURRENT_TURNS``)
varios turnos HTTP/A2A pueden correr en paralelo: cada uno ya está aislado por su
propio ``chat_id``/``thread_id`` en el checkpointer, así que correrlos a la vez no
mezcla estado entre conversaciones distintas. Con ``allow_concurrent_turns=False`` es
un run por turno: un turno nuevo se rechaza mientras haya uno en curso. En ambos casos
un contador interno (``try_begin_task``/``end_task``) lleva la cuenta de turnos activos,
así que ``status`` solo vuelve a ``UP`` cuando termina el último.
"""

from __future__ import annotations

from type_defs import StatusAgent


class AgentState:
    """Estado compartido del agente (uso en servicio HTTP)."""

    def __init__(self) -> None:
        self._status: StatusAgent = "DOWN"
        self._shutdown_requested = False
        self._active_tasks = 0
        self._allow_concurrent_turns = True

    @property
    def status(self) -> StatusAgent:
        """Obtener el estado actual del agente."""
        return self._status

    def set_status(self, value: StatusAgent) -> None:
        """Establecer el estado actual del agente y reiniciar el conteo de turnos en curso.

        Uso reservado a transiciones externas (arranque/parada del agente, tests); los
        turnos individuales se registran con ``try_begin_task``/``end_task``, que no
        pasan por aquí.
        """
        self._status = value
        self._active_tasks = 0

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

    @property
    def allow_concurrent_turns(self) -> bool:
        """Si True, varios turnos pueden correr a la vez (``HTTP_ALLOW_CONCURRENT_TURNS``)."""
        return self._allow_concurrent_turns

    def set_allow_concurrent_turns(self, value: bool) -> None:
        """Fija la política de concurrencia (se establece una vez al arrancar el agente)."""
        self._allow_concurrent_turns = value

    def try_begin_task(self) -> bool:
        """Intenta reservar un turno nuevo; retorna si quedó registrado.

        Con ``allow_concurrent_turns=False`` y un turno ya en curso, no registra nada y
        retorna ``False``. En cualquier otro caso suma al contador interno, pasa el
        estado a ``DOING_TASK`` y retorna ``True``. Sin ningún ``await`` de por medio, la
        operación es atómica frente a otras corrutinas del mismo loop de asyncio.
        """
        if self._active_tasks > 0 and not self._allow_concurrent_turns:
            return False
        self._active_tasks += 1
        self._status = "DOING_TASK"
        return True

    def end_task(self) -> None:
        """Registra el fin de un turno; vuelve a UP solo cuando no queda ninguno en curso."""
        self._active_tasks = max(0, self._active_tasks - 1)
        if self._active_tasks == 0 and not self._shutdown_requested:
            self._status = "UP"


agent_state = AgentState()
