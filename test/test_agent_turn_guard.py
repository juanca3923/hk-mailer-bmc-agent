"""Unit tests for ``AgentState`` turn bookkeeping.

Covers the ``HTTP_ALLOW_CONCURRENT_TURNS`` policy: True (default) allows concurrent
turns while still tracking DOING_TASK/UP correctly via the internal counter; False
rejects a new turn while one is already in progress.
"""

from __future__ import annotations

from http_api.state import AgentState


def test_default_allows_concurrent_turns() -> None:
    state = AgentState()
    assert state.allow_concurrent_turns is True


def test_try_begin_task_allows_concurrent_turns_by_default() -> None:
    state = AgentState()
    assert state.try_begin_task() is True
    assert state.try_begin_task() is True
    assert state.status == "DOING_TASK"


def test_try_begin_task_blocks_second_turn_when_disabled() -> None:
    state = AgentState()
    state.set_allow_concurrent_turns(False)
    assert state.try_begin_task() is True
    assert state.status == "DOING_TASK"
    assert state.try_begin_task() is False
    assert state.status == "DOING_TASK"


def test_end_task_restores_up_only_when_no_turn_is_left() -> None:
    state = AgentState()
    state.try_begin_task()
    state.try_begin_task()
    state.end_task()
    assert state.status == "DOING_TASK"
    state.end_task()
    assert state.status == "UP"


def test_end_task_is_a_no_op_without_a_matching_begin() -> None:
    """El contador nunca debe bajar de 0 aunque ``end_task`` se llame de más."""
    state = AgentState()
    state.end_task()
    state.end_task()
    assert state.status == "UP"


def test_end_task_does_not_restore_up_when_shutdown_requested() -> None:
    state = AgentState()
    state.try_begin_task()
    state.request_shutdown()
    state.end_task()
    assert state.status == "DOING_TASK"


def test_set_status_resets_active_task_counter() -> None:
    """``set_status`` es para transiciones externas (arranque/parada); reinicia el conteo."""
    state = AgentState()
    state.try_begin_task()
    state.set_status("UP")
    state.end_task()  # sin turno pendiente tras el reset: no debe romper el estado
    assert state.status == "UP"
