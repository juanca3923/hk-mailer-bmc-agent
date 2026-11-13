"""Helpers compartidos de escritura con guardas y de herramientas de tickets."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import BaseModel

from agent.internal_tools.ticket_tool_helpers import search_detail_json, work_log_options
from commons.bmc.guarded_write import run_guarded_write, work_log_fields
from commons.bmc.ticket_guards import require_submitter
from constants.bmc import USER_ERROR_MESSAGE_TICKET_ALREADY_CLOSED, USER_ERROR_MESSAGE_WRITE_DISABLED
from exception.mcp import MCPClientError
from type_defs.models.bmc.ar_api import BmcEntry, BmcEntryListResponse, BmcEntryValues
from type_defs.models.bmc.inputs import AddIncidentNoteInput, AddWorkOrderNoteInput, WorkLogInput
from type_defs.models.bmc.outputs import BaseOutput
from type_defs.models.bmc.ticket_state import TicketState

OPEN_STATE = TicketState(request_id='REQ1', status='In Progress', submitter='svc')
MISSING = 'falta el id'
DONE = BaseOutput(success=True, message='hecho')


class Handler:
    def __init__(self, *, allow_write: bool = True) -> None:
        self.allow_write = allow_write

    def ensure_write_allowed(self) -> BaseOutput | None:
        return None if self.allow_write else BaseOutput(success=False, message=USER_ERROR_MESSAGE_WRITE_DISABLED)


class Probe:
    """Records which steps of ``run_guarded_write`` actually ran."""

    def __init__(self, state: TicketState | None = OPEN_STATE, error: BaseOutput | None = None) -> None:
        self.state = state
        self.error = error
        self.resolved = 0
        self.acted_on: list[TicketState] = []
        self.action_error: MCPClientError | None = None

    async def resolve(self) -> tuple[TicketState | None, BaseOutput | None]:
        self.resolved += 1
        return self.state, self.error

    async def action(self, state: TicketState) -> BaseOutput:
        if self.action_error is not None:
            raise self.action_error
        self.acted_on.append(state)
        return DONE


async def _run(probe: Probe, handler: Handler | None = None, **kwargs: Any) -> BaseOutput:
    return await run_guarded_write(
        handler or Handler(), resolve=probe.resolve, missing_message=MISSING, action=probe.action, **kwargs
    )


async def test_disabled_writes_return_the_block_without_resolving_the_ticket() -> None:
    probe = Probe()

    result = await _run(probe, Handler(allow_write=False))

    assert result.message == USER_ERROR_MESSAGE_WRITE_DISABLED
    assert probe.resolved == 0
    assert probe.acted_on == []


async def test_a_resolution_error_is_returned_and_the_action_never_runs() -> None:
    error = BaseOutput(success=False, message='no existe')
    probe = Probe(state=None, error=error)

    result = await _run(probe)

    assert result == error
    assert probe.acted_on == []


async def test_missing_state_without_error_returns_the_missing_message() -> None:
    probe = Probe(state=None, error=None)

    result = await _run(probe)

    assert (result.success, result.message) == (False, MISSING)


async def test_closed_ticket_is_rejected() -> None:
    probe = Probe(state=TicketState('REQ1', 'Closed', 'svc'))

    result = await _run(probe)

    assert (result.success, result.message) == (False, USER_ERROR_MESSAGE_TICKET_ALREADY_CLOSED)
    assert probe.acted_on == []


async def test_extra_guard_runs_after_the_closed_check_and_can_reject() -> None:
    probe = Probe()

    result = await _run(probe, extra_guard=lambda state: require_submitter(state.submitter, 'otro'))

    assert result.success is False
    assert 'svc' in result.message
    assert probe.acted_on == []


async def test_extra_guard_is_skipped_for_closed_tickets() -> None:
    probe = Probe(state=TicketState('REQ1', 'Closed', 'svc'))
    calls: list[TicketState] = []

    def guard(state: TicketState) -> None:
        calls.append(state)

    await _run(probe, extra_guard=guard)

    assert calls == []


async def test_the_action_output_is_returned_when_every_guard_passes() -> None:
    probe = Probe()

    result = await _run(probe, extra_guard=lambda state: require_submitter(state.submitter, 'svc'))

    assert result == DONE
    assert probe.acted_on == [OPEN_STATE]


async def test_a_bmc_error_in_the_action_becomes_a_failed_output() -> None:
    probe = Probe()
    probe.action_error = MCPClientError('BMC caído')

    result = await _run(probe)

    assert (result.success, result.message) == (False, 'BMC caído')


def test_work_log_fields_map_the_note_inputs_of_both_ticket_types() -> None:
    incident = AddIncidentNoteInput(
        incident_number='INC1', note_text='hola', work_log_type='Resolution', view_access='Internal'
    )
    work_order = AddWorkOrderNoteInput(work_order_id='WO1', note_text='hola', secure_work_log='Yes')

    assert work_log_fields(incident) == {
        'work_log_type': 'Resolution',
        'view_access': 'Internal',
        'secure_work_log': 'No',
        'detailed_description': 'hola',
    }
    assert work_log_fields(work_order)['secure_work_log'] == 'Yes'


def test_both_note_inputs_share_the_work_log_base_with_unchanged_defaults() -> None:
    assert issubclass(AddIncidentNoteInput, WorkLogInput)
    assert issubclass(AddWorkOrderNoteInput, WorkLogInput)
    base = WorkLogInput(note_text='x')
    assert (base.work_log_type, base.view_access, base.secure_work_log) == ('General Information', 'Public', 'No')


def test_work_log_options_collects_the_tool_arguments() -> None:
    assert work_log_options('nota', 'General Information', 'Public', 'No') == {
        'note_text': 'nota',
        'work_log_type': 'General Information',
        'view_access': 'Public',
        'secure_work_log': 'No',
    }


class Detail(BaseModel):
    title: str


def _search(entries: list[dict[str, Any]], error: MCPClientError | None = None) -> Any:
    async def search() -> BmcEntryListResponse:
        if error is not None:
            raise error
        return BmcEntryListResponse(entries=[BmcEntry(values=BmcEntryValues(data=data)) for data in entries])

    return search()


async def test_search_detail_json_encodes_the_detail_of_the_first_entry() -> None:
    raw = await search_detail_json(
        _search([{'Description': 'Falla'}]),
        not_found_message='no está',
        build_detail=lambda data: Detail(title=str(data['Description'])),
    )

    payload = json.loads(raw)
    assert payload['success'] is True
    assert 'Falla' in payload['message']


@pytest.mark.parametrize(('entries', 'error', 'message'), [
    ([], None, 'no está'),
    ([{'Description': 'x'}], MCPClientError('BMC caído'), 'BMC caído'),
])
async def test_search_detail_json_reports_not_found_and_client_errors(
    entries: list[dict[str, Any]], error: MCPClientError | None, message: str
) -> None:
    raw = await search_detail_json(
        _search(entries, error),
        not_found_message='no está',
        build_detail=lambda data: Detail(title=str(data)),
    )

    assert json.loads(raw) == {'success': False, 'message': message}
