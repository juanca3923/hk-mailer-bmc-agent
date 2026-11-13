"""Unit tests for Incident business-rule guards (close ownership, reopen, ownership)."""

from constants.bmc import AR_FIELD_REQUEST_ID, AR_FIELD_STATUS, AR_FIELD_SUBMITTER
from services.bmc.incident_operations import IncidentOperations
from type_defs.models.bmc.ar_api import BmcEntry, BmcEntryListResponse, BmcEntryValues
from type_defs.models.bmc.inputs import AddIncidentNoteInput, CloseIncidentInput


class FakeSettings:
    """Minimal stand-in for BmcSettings exposing ``username`` and ``assignee_display_name``."""

    def __init__(self, username: str, assignee_display_name: str) -> None:
        self.username = username
        self.assignee_display_name = assignee_display_name


class FakeClient:
    """Records write calls and returns a configurable search result."""

    def __init__(self, status: str, submitter: str, request_id: str = 'REQ001') -> None:
        self._status = status
        self._submitter = submitter
        self._request_id = request_id
        self.update_calls: list[tuple[str, dict]] = []
        self.post_incident_work_log_calls: list[object] = []

    async def search_incident(self, incident_number: str) -> BmcEntryListResponse:  # noqa: ARG002
        values = BmcEntryValues(
            data={
                AR_FIELD_REQUEST_ID: self._request_id,
                AR_FIELD_STATUS: self._status,
                AR_FIELD_SUBMITTER: self._submitter,
            },
        )
        return BmcEntryListResponse(entries=[BmcEntry(values=values)])

    async def update_incident(self, request_id: str, json_body: dict) -> dict:
        self.update_calls.append((request_id, json_body))
        return {}

    async def post_incident_work_log(self, body: object) -> dict:
        self.post_incident_work_log_calls.append(body)
        return {}


class FakeHandler:
    """Minimal stand-in for BaseToolHandler used by IncidentOperations."""

    def __init__(
        self,
        client: FakeClient,
        username: str = 'svc_mosaico',
        assignee_display_name: str = 'Mosaico WebServices',
    ) -> None:
        self.client = client
        self.settings = FakeSettings(username, assignee_display_name)

    def ensure_write_allowed(self) -> None:
        return None

    def load_attachment(self, file_path: str) -> None:  # noqa: ARG002
        raise AssertionError('load_attachment should not be called in these tests')


async def test_close_rejected_when_not_owner() -> None:
    client = FakeClient(status='In Progress', submitter='otro_usuario')
    handler = FakeHandler(client, username='svc_mosaico')
    result = await IncidentOperations(handler).close(
        CloseIncidentInput(incident_number='INC1', description='close'),
    )
    assert result.success is False
    assert 'otro_usuario' in result.message
    assert client.update_calls == []


async def test_close_succeeds_when_in_progress_and_owner() -> None:
    client = FakeClient(status='In Progress', submitter='svc_mosaico')
    handler = FakeHandler(client, username='svc_mosaico')
    result = await IncidentOperations(handler).close(
        CloseIncidentInput(incident_number='INC1', description='close'),
    )
    assert result.success is True
    expected_put_calls = 2  # ownership+In Progress PUT, final Resolved PUT
    assert len(client.update_calls) == expected_put_calls
    _, ownership_body = client.update_calls[0]
    assert ownership_body['values']['Status'] == 'In Progress'
    assert ownership_body['values']['Assignee'] == 'Mosaico WebServices'
    _, final_body = client.update_calls[1]
    assert final_body['values']['Status'] == 'Resolved'
    assert final_body['values']['Status_Reason'] == 'Closing'


async def test_close_succeeds_from_assigned_takes_ownership_and_progresses() -> None:
    client = FakeClient(status='Assigned', submitter='svc_mosaico')
    handler = FakeHandler(client, username='svc_mosaico')
    result = await IncidentOperations(handler).close(
        CloseIncidentInput(incident_number='INC1', description='close'),
    )
    assert result.success is True
    expected_put_calls = 2
    assert len(client.update_calls) == expected_put_calls
    _, ownership_body = client.update_calls[0]
    assert ownership_body['values']['Status'] == 'In Progress'
    assert ownership_body['values']['Assignee'] == 'Mosaico WebServices'


async def test_close_rejected_when_already_closed() -> None:
    client = FakeClient(status='Closed', submitter='svc_mosaico')
    handler = FakeHandler(client, username='svc_mosaico')
    result = await IncidentOperations(handler).close(
        CloseIncidentInput(incident_number='INC1', description='close'),
    )
    assert result.success is False
    assert client.update_calls == []


async def test_add_note_rejected_when_closed() -> None:
    client = FakeClient(status='Closed', submitter='svc_mosaico')
    result = await IncidentOperations(FakeHandler(client)).add_note(
        AddIncidentNoteInput(incident_number='INC1', note_text='hola'),
    )
    assert result.success is False
    assert client.post_incident_work_log_calls == []


async def test_add_note_allowed_on_open_ticket_of_another_owner() -> None:
    client = FakeClient(status='Assigned', submitter='otro_usuario')
    handler = FakeHandler(client, username='svc_mosaico')
    result = await IncidentOperations(handler).add_note(
        AddIncidentNoteInput(incident_number='INC1', note_text='hola'),
    )
    assert result.success is True
    assert len(client.post_incident_work_log_calls) == 1
