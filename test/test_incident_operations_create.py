"""Unit tests for IncidentOperations.create() and the categorization fallback workaround."""

from bmc.libs.constants import (
    AR_FIELD_CATEGORIZATION_TIER_1,
    AR_FIELD_CATEGORIZATION_TIER_2,
    AR_FIELD_INCIDENT_NUMBER,
    AR_FIELD_REQUEST_ID,
    DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_TIER_1,
    DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_TIER_2,
)
from bmc.libs.helpers.incident_operations import IncidentOperations
from bmc.type_defs.ar_api import BmcCreateEntryResponse, BmcEntry, BmcEntryListResponse, BmcEntryValues
from bmc.type_defs.inputs import CreateIncidentInput


class FakeClient:
    """Records create/search/update/work-log calls with a configurable search result."""

    def __init__(self, search_tier1: str, search_tier2: str, request_id: str = 'REQ001') -> None:
        self._search_tier1 = search_tier1
        self._search_tier2 = search_tier2
        self._request_id = request_id
        self.update_calls: list[tuple[str, dict]] = []
        self.post_incident_work_log_calls: list[object] = []

    async def create_incident_entry(self, json_body: dict) -> BmcCreateEntryResponse:  # noqa: ARG002
        return BmcCreateEntryResponse(
            values=BmcEntryValues(data={AR_FIELD_INCIDENT_NUMBER: 'INC1', 'Description': 'D'}),
        )

    async def search_incident(self, incident_number: str) -> BmcEntryListResponse:  # noqa: ARG002
        values = BmcEntryValues(
            data={
                AR_FIELD_REQUEST_ID: self._request_id,
                AR_FIELD_CATEGORIZATION_TIER_1: self._search_tier1,
                AR_FIELD_CATEGORIZATION_TIER_2: self._search_tier2,
            },
        )
        return BmcEntryListResponse(entries=[BmcEntry(values=values)])

    async def update_incident(self, request_id: str, json_body: dict) -> dict:
        self.update_calls.append((request_id, json_body))
        return {}

    async def post_incident_work_log(self, body: object) -> dict:
        self.post_incident_work_log_calls.append(body)
        return {}


class FakeSettings:
    """Stand-in for the subset of BmcSettings used by IncidentOperations.create()."""

    default_first_name = 'Mosaico'
    default_last_name = 'WebServices'


class FakeHandler:
    """Minimal stand-in for BaseToolHandler used by IncidentOperations."""

    def __init__(self, client: FakeClient) -> None:
        self.client = client
        self.settings = FakeSettings()

    def ensure_write_allowed(self) -> None:
        return None


def _create_input() -> CreateIncidentInput:
    return CreateIncidentInput(
        description='D',
        detailed_decription='DD',
        categorization_tier_1='T1',
        categorization_tier_2='T2',
        product_categorization_tier_1='P1',
        product_categorization_tier_2='P2',
        product_categorization_tier_3='P3',
        assigned_group='GTI.GROUP',
    )


async def test_create_incident_no_fallback_when_categorization_filled() -> None:
    client = FakeClient(search_tier1='T1', search_tier2='T2')
    result = await IncidentOperations(FakeHandler(client)).create(_create_input())
    assert result.success is True
    assert client.update_calls == []
    assert client.post_incident_work_log_calls == []
    assert 'categorization_fallback_applied: false' in result.message


async def test_create_incident_applies_categorization_fallback_when_empty() -> None:
    client = FakeClient(search_tier1='', search_tier2='')
    result = await IncidentOperations(FakeHandler(client)).create(_create_input())
    assert result.success is True
    assert len(client.update_calls) == 1
    request_id, body = client.update_calls[0]
    assert request_id == 'REQ001'
    assert body['values'][AR_FIELD_CATEGORIZATION_TIER_1] == DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_TIER_1
    assert body['values'][AR_FIELD_CATEGORIZATION_TIER_2] == DEFAULT_INCIDENT_CATEGORIZATION_FALLBACK_TIER_2
    assert len(client.post_incident_work_log_calls) == 1
    assert 'categorization_fallback_applied: true' in result.message


async def test_create_incident_skips_fallback_without_request_id() -> None:
    client = FakeClient(search_tier1='', search_tier2='', request_id='')
    result = await IncidentOperations(FakeHandler(client)).create(_create_input())
    assert result.success is True
    assert client.update_calls == []
    assert client.post_incident_work_log_calls == []
    assert 'categorization_fallback_applied: false' in result.message
