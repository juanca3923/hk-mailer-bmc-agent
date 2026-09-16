"""Unit tests for the bmc_* LangChain tools: guard delegation and contract regressions."""

from __future__ import annotations

import json

import pydantic
import pytest

from agent.internal_tools import bmc_tools
from bmc.libs.business_defaults import DEFAULT_WORK_ORDER_SUPPORT_COMPANY, DEFAULT_WORK_ORDER_SUPPORT_ORGANIZATION
from bmc.libs.constants import (
    AR_FIELD_PEOPLE_FIRST_NAME,
    AR_FIELD_PEOPLE_LAST_NAME,
    AR_FIELD_PEOPLE_LOGIN_ID,
    AR_FIELD_REQUEST_ID,
    AR_FIELD_STATUS,
    AR_FIELD_SUBMITTER,
    AR_FIELD_WORK_ORDER_ID_RESPONSE,
    INCIDENT_DESCRIPTION_MAX_LENGTH,
    INCIDENT_STATUSES,
    WORK_ORDER_STATUSES,
)
from bmc.type_defs.ar_api import BmcCreateEntryResponse, BmcEntry, BmcEntryListResponse, BmcEntryValues
from bmc.type_defs.inputs import CloseIncidentInput, CreateIncidentInput

REPORTER_EMAIL = 'ana.reportante@arus.com.co'


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

    def __init__(
        self,
        status: str = 'Assigned',
        submitter: str = 'svc_mosaico',
        request_id: str = 'REQ001',
        person_entries: list[BmcEntry] | None = None,
    ) -> None:
        self._status = status
        self._submitter = submitter
        self._request_id = request_id
        self._person_entries = (
            [BmcEntry(values=BmcEntryValues(data={
                AR_FIELD_PEOPLE_LOGIN_ID: 'ana.reportante@arus.com.co',
                AR_FIELD_PEOPLE_FIRST_NAME: 'Ana',
                AR_FIELD_PEOPLE_LAST_NAME: 'Reportante',
            }))]
            if person_entries is None
            else person_entries
        )
        self.update_calls: list[tuple[str, dict]] = []
        self.post_incident_work_log_calls: list[object] = []
        self.create_work_order_calls: list[dict] = []
        self.create_incident_calls: list[dict] = []
        self.search_person_by_email_calls: list[str] = []

    async def create_work_order_entry(self, json_body: dict) -> BmcCreateEntryResponse:
        self.create_work_order_calls.append(json_body)
        return BmcCreateEntryResponse(
            values=BmcEntryValues(data={AR_FIELD_WORK_ORDER_ID_RESPONSE: 'WO1', 'Summary': 'S'}),
        )

    async def search_person_by_email(self, email: str) -> BmcEntryListResponse:
        self.search_person_by_email_calls.append(email)
        return BmcEntryListResponse(entries=self._person_entries)

    async def create_incident_entry(self, json_body: dict) -> BmcCreateEntryResponse:
        self.create_incident_calls.append(json_body)
        return BmcCreateEntryResponse(
            values=BmcEntryValues(data={'Incident Number': 'INC1', 'Description': 'D'}),
        )

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
def _reset_handler_singleton() -> None:
    """Ensure each test starts from a clean cached ``_get_handler`` singleton."""
    bmc_tools._get_handler.cache_clear()


async def test_bmc_close_work_order_reflects_guard_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient(status='Closed', submitter='svc_mosaico')
    monkeypatch.setattr(bmc_tools, '_get_handler', lambda: FakeHandler(client))

    raw = await bmc_tools.bmc_close_work_order.ainvoke({'work_order_id': 'WO1'})

    payload = json.loads(raw)
    assert payload['success'] is False
    assert client.update_calls == []


async def test_bmc_close_incident_reflects_guard_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient(status='In Progress', submitter='otro_usuario')
    monkeypatch.setattr(bmc_tools, '_get_handler', lambda: FakeHandler(client))

    raw = await bmc_tools.bmc_close_incident.ainvoke({'incident_number': 'INC1', 'description': 'cierre'})

    payload = json.loads(raw)
    assert payload['success'] is False
    assert 'otro_usuario' in payload['message']
    assert client.update_calls == []


async def test_bmc_add_incident_note_uses_work_log_not_work_info(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient(status='Assigned', submitter='svc_mosaico')
    monkeypatch.setattr(bmc_tools, '_get_handler', lambda: FakeHandler(client))

    raw = await bmc_tools.bmc_add_incident_note.ainvoke({'incident_number': 'INC1', 'note_text': 'hola'})

    payload = json.loads(raw)
    assert payload['success'] is True
    assert len(client.post_incident_work_log_calls) == 1


def test_bmc_create_incident_has_no_impact_urgency_params_but_has_assigned_group() -> None:
    schema_keys = set(bmc_tools.bmc_create_incident.args.keys())
    assert 'impact' not in schema_keys
    assert 'urgency' not in schema_keys
    assert 'assigned_support_company' not in schema_keys
    assert 'assigned_support_organization' not in schema_keys
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


def test_bmc_create_work_order_has_no_support_company_organization_params_but_has_assigned_group() -> None:
    schema_keys = set(bmc_tools.bmc_create_work_order.args.keys())
    assert 'support_company' not in schema_keys
    assert 'support_organization' not in schema_keys
    assert 'assigned_group' in schema_keys


async def test_bmc_create_work_order_sends_support_company_and_organization(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient()
    monkeypatch.setattr(bmc_tools, '_get_handler', lambda: FakeHandler(client))

    raw = await bmc_tools.bmc_create_work_order.ainvoke({
        'summary': 'S',
        'detailed_description': 'DD',
        'reporter_email': REPORTER_EMAIL,
        'categorization_tier_1': 'T1',
        'categorization_tier_2': 'T2',
        'product_cat_tier_1': 'P1',
        'product_cat_tier_2': 'P2',
        'product_cat_tier_3': 'P3',
        'assigned_group': 'GTI.GROUP',
    })

    payload = json.loads(raw)
    assert payload['success'] is True
    assert len(client.create_work_order_calls) == 1
    assert client.search_person_by_email_calls == [REPORTER_EMAIL]
    body_values = client.create_work_order_calls[0]['values']
    assert body_values['Support Company'] == DEFAULT_WORK_ORDER_SUPPORT_COMPANY
    assert body_values['Support Organization'] == DEFAULT_WORK_ORDER_SUPPORT_ORGANIZATION
    assert body_values['Support Group Name'] == 'GTI.GROUP'
    assert body_values['First Name'] == 'Ana'
    assert body_values['Last Name'] == 'Reportante'


async def test_bmc_create_work_order_fails_closed_when_reporter_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient(person_entries=[])
    monkeypatch.setattr(bmc_tools, '_get_handler', lambda: FakeHandler(client))

    raw = await bmc_tools.bmc_create_work_order.ainvoke({
        'summary': 'S',
        'detailed_description': 'DD',
        'reporter_email': REPORTER_EMAIL,
        'categorization_tier_1': 'T1',
        'categorization_tier_2': 'T2',
        'product_cat_tier_1': 'P1',
        'product_cat_tier_2': 'P2',
        'product_cat_tier_3': 'P3',
    })

    payload = json.loads(raw)
    assert payload['success'] is False
    assert REPORTER_EMAIL in payload['message']
    assert client.create_work_order_calls == []


async def test_bmc_create_incident_uses_looked_up_reporter_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient()
    monkeypatch.setattr(bmc_tools, '_get_handler', lambda: FakeHandler(client))

    raw = await bmc_tools.bmc_create_incident.ainvoke({
        'description': 'D',
        'detailed_decription': 'DD',
        'reporter_email': REPORTER_EMAIL,
        'product_categorization_tier_1': 'P1',
        'product_categorization_tier_2': 'P2',
        'product_categorization_tier_3': 'P3',
    })

    payload = json.loads(raw)
    assert payload['success'] is True
    assert len(client.create_incident_calls) == 1
    assert client.search_person_by_email_calls == [REPORTER_EMAIL]
    body_values = client.create_incident_calls[0]['values']
    assert body_values['First_Name'] == 'Ana'
    assert body_values['Last_Name'] == 'Reportante'


async def test_bmc_create_incident_fails_closed_when_reporter_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient(person_entries=[])
    monkeypatch.setattr(bmc_tools, '_get_handler', lambda: FakeHandler(client))

    raw = await bmc_tools.bmc_create_incident.ainvoke({
        'description': 'D',
        'detailed_decription': 'DD',
        'reporter_email': REPORTER_EMAIL,
        'product_categorization_tier_1': 'P1',
        'product_categorization_tier_2': 'P2',
        'product_categorization_tier_3': 'P3',
    })

    payload = json.loads(raw)
    assert payload['success'] is False
    assert REPORTER_EMAIL in payload['message']
    assert client.create_incident_calls == []


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


def test_incident_description_fields_expose_100_char_limit_to_the_model() -> None:
    """BMC rejects the whole request (not a truncation) above 100 chars on this
    AR field — regression for 'Value does not fall within the limits specified
    for the field... Maximum length -100'."""
    assert bmc_tools.bmc_create_incident.args['description']['maxLength'] == INCIDENT_DESCRIPTION_MAX_LENGTH
    assert bmc_tools.bmc_close_incident.args['description']['maxLength'] == INCIDENT_DESCRIPTION_MAX_LENGTH


def test_create_incident_input_rejects_description_over_100_chars() -> None:
    with pytest.raises(pydantic.ValidationError):
        CreateIncidentInput(
            description='x' * (INCIDENT_DESCRIPTION_MAX_LENGTH + 1),
            detailed_decription='detalle',
            reporter_email=REPORTER_EMAIL,
            product_categorization_tier_1='P1',
            product_categorization_tier_2='P2',
            product_categorization_tier_3='P3',
        )


def test_close_incident_input_rejects_description_over_100_chars() -> None:
    with pytest.raises(pydantic.ValidationError):
        CloseIncidentInput(incident_number='INC1', description='x' * (INCIDENT_DESCRIPTION_MAX_LENGTH + 1))


def test_bmc_create_work_order_requires_categorization_params_explicitly() -> None:
    """No code-level catch-all: the LLM must always pass these five, sourced from a
    domain skill row or from guia-creacion-tickets' documented catch-all values —
    editable by the service desk without redeploying the agent."""
    schema = bmc_tools.bmc_create_work_order.args_schema
    for field_name in (
        'categorization_tier_1',
        'categorization_tier_2',
        'product_cat_tier_1',
        'product_cat_tier_2',
        'product_cat_tier_3',
    ):
        assert schema.model_fields[field_name].is_required()


def test_all_bmc_tool_params_expose_a_description() -> None:
    """Regression for the tool-calling standard: every parameter must carry its own
    description in the JSON schema the model sees, not only in the function docstring."""
    for t in bmc_tools._ALL_BMC_TOOLS:  # noqa: SLF001
        schema = t.args_schema.model_json_schema() if t.args_schema else {'properties': {}}
        for name, prop in schema.get('properties', {}).items():
            assert 'description' in prop, f'{t.name}.{name} missing description'
