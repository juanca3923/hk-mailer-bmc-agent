"""Unit tests for the bmc_* LangChain tools: guard delegation and contract regressions."""

from __future__ import annotations

import json

import pytest

from agent.internal_tools import bmc_tools
from bmc.libs.constants import (
    AR_FIELD_REQUEST_ID,
    AR_FIELD_STATUS,
    AR_FIELD_SUBMITTER,
    INCIDENT_STATUSES,
    WORK_ORDER_STATUSES,
)
from bmc.type_defs.ar_api import BmcEntry, BmcEntryListResponse, BmcEntryValues


class FakeSettings:
    """Minimal stand-in for BmcSettings exposing ``username`` and ``assignee_display_name``."""

    def __init__(self, username: str = 'svc_mosaico', assignee_display_name: str = 'Mosaico WebServices') -> None:
        self.username = username
        self.assignee_display_name = assignee_display_name


class FakeClient:
    """Records write calls; deliberately has no ``post_work_info`` for incident tests.

    If incident note/attachment code regresses to calling ``post_work_info`` (the Work
    Order form) instead of ``post_incident_work_log`` (``HPD:WorkLog``), the call raises
    ``AttributeError`` instead of silently succeeding against the wrong form.
    """

    def __init__(self, status: str = 'Assigned', submitter: str = 'svc_mosaico', request_id: str = 'REQ001') -> None:
        self._status = status
        self._submitter = submitter
        self._request_id = request_id
        self.update_calls: list[tuple[str, dict]] = []
        self.post_incident_work_log_calls: list[object] = []

    async def search_work_order(self, work_order_id: str) -> BmcEntryListResponse:  # noqa: ARG002
        return self._search_result()

    async def search_incident(self, incident_number: str) -> BmcEntryListResponse:  # noqa: ARG002
        return self._search_result()

    def _search_result(self) -> BmcEntryListResponse:
        values = BmcEntryValues(
            data={
                AR_FIELD_REQUEST_ID: self._request_id,
                AR_FIELD_STATUS: self._status,
                AR_FIELD_SUBMITTER: self._submitter,
            },
        )
        return BmcEntryListResponse(entries=[BmcEntry(values=values)])

    async def update_work_order(self, request_id: str, json_body: dict) -> dict:
        self.update_calls.append((request_id, json_body))
        return {}

    async def update_incident(self, request_id: str, json_body: dict) -> dict:
        self.update_calls.append((request_id, json_body))
        return {}

    async def post_incident_work_log(self, body: object) -> dict:
        self.post_incident_work_log_calls.append(body)
        return {}


class FakeHandler:
    """Minimal stand-in for BaseToolHandler used by the bmc_* tools."""

    def __init__(self, client: FakeClient) -> None:
        self.client = client
        self.settings = FakeSettings()

    def ensure_write_allowed(self) -> None:
        return None

    def load_attachment(self, file_path: str) -> None:  # noqa: ARG002
        raise AssertionError('load_attachment should not be called in these tests')


@pytest.fixture(autouse=True)
def _reset_handler_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure each test starts from a clean module-level ``_handler`` singleton."""
    monkeypatch.setattr(bmc_tools, '_handler', None)


async def test_bmc_close_work_order_reflects_guard_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient(status='Closed', submitter='svc_mosaico')
    monkeypatch.setattr(bmc_tools, '_handler', FakeHandler(client))

    raw = await bmc_tools.bmc_close_work_order.ainvoke({'work_order_id': 'WO1'})

    payload = json.loads(raw)
    assert payload['success'] is False
    assert client.update_calls == []


async def test_bmc_close_incident_reflects_guard_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient(status='In Progress', submitter='otro_usuario')
    monkeypatch.setattr(bmc_tools, '_handler', FakeHandler(client))

    raw = await bmc_tools.bmc_close_incident.ainvoke({'incident_number': 'INC1', 'description': 'cierre'})

    payload = json.loads(raw)
    assert payload['success'] is False
    assert 'otro_usuario' in payload['message']
    assert client.update_calls == []


async def test_bmc_add_incident_note_uses_work_log_not_work_info(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient(status='Assigned', submitter='svc_mosaico')
    monkeypatch.setattr(bmc_tools, '_handler', FakeHandler(client))

    raw = await bmc_tools.bmc_add_incident_note.ainvoke({'incident_number': 'INC1', 'note_text': 'hola'})

    payload = json.loads(raw)
    assert payload['success'] is True
    assert len(client.post_incident_work_log_calls) == 1


def test_bmc_create_incident_has_no_impact_urgency_params_but_has_assigned_group() -> None:
    schema_keys = set(bmc_tools.bmc_create_incident.args.keys())
    assert 'impact' not in schema_keys
    assert 'urgency' not in schema_keys
    assert 'assigned_group' in schema_keys


def test_bmc_close_work_order_has_no_obsolete_status_params() -> None:
    schema_keys = set(bmc_tools.bmc_close_work_order.args.keys())
    assert 'status_reason' not in schema_keys
    assert 'final_status' not in schema_keys
    assert 'description' not in schema_keys


def test_bmc_close_incident_has_no_obsolete_status_params() -> None:
    schema_keys = set(bmc_tools.bmc_close_incident.args.keys())
    assert 'status_reason' not in schema_keys
    assert 'intermediate_status' not in schema_keys
    assert 'final_status' not in schema_keys


def test_bmc_create_work_order_has_assigned_group_param() -> None:
    schema_keys = set(bmc_tools.bmc_create_work_order.args.keys())
    assert 'assigned_group' in schema_keys


def test_status_params_expose_enum_to_the_model() -> None:
    for tool_fn, statuses in (
        (bmc_tools.bmc_create_work_order, WORK_ORDER_STATUSES),
        (bmc_tools.bmc_update_work_order_status, WORK_ORDER_STATUSES),
        (bmc_tools.bmc_create_incident, INCIDENT_STATUSES),
    ):
        assert set(tool_fn.args['status'].get('enum', [])) == set(statuses)


def test_all_bmc_tools_are_prefixed() -> None:
    for t in bmc_tools._ALL_BMC_TOOLS:  # noqa: SLF001
        assert t.name.startswith('bmc_')
