"""Async HTTP client for the BMC Helix AR REST API."""

import json
import logging
from http import HTTPStatus
from typing import cast
from urllib.parse import quote

import httpx

from commons.bmc.ar_query_builder import ArQueryBuilder
from commons.bmc.multipart_builder import HttpxMultipartParts, WorkInfoMultipartBody
from config.bmc_settings import BmcSettings
from constants.bmc import (
    API_PATH_ARSYS_ENTRY_PREFIX,
    AR_FIELD_INCIDENT_NUMBER,
    AR_FIELD_INCIDENT_REPORTER_EMAIL,
    AR_FIELD_PEOPLE_EMAIL,
    AR_FIELD_PEOPLE_FIRST_NAME,
    AR_FIELD_PEOPLE_LAST_NAME,
    AR_FIELD_PEOPLE_LOGIN_ID,
    AR_FIELD_PEOPLE_STATUS,
    AR_FIELD_REQUEST_ID,
    AR_FIELD_WO_CUSTOMER_EMAIL,
    AR_FIELD_WORK_ORDER_ID,
    AR_FIELD_WORK_ORDER_ID_RESPONSE,
    USER_ERROR_MESSAGE_INVALID_JSON,
    USER_ERROR_MESSAGE_NETWORK,
    USER_ERROR_MESSAGE_TIMEOUT,
    USER_ERROR_MESSAGE_UNEXPECTED,
    USER_ERROR_MESSAGES,
)
from exception.mcp import MCPClientError
from services.bmc.connection_manager import BmcConnectionManager
from type_defs.models.bmc.ar_api import (
    BmcCreateEntryResponse,
    BmcEntryListResponse,
    parse_create_response,
    parse_entry_list,
)
from type_defs.models.bmc.json_types import JsonValue

logger = logging.getLogger(__name__)


class BmcClient:
    """Thin async wrapper around BMC AR REST with session from ``BmcConnectionManager``.

    Attributes
    ----------
    _settings : BmcSettings
        BMC form names, URLs, and timeouts.
    _manager : BmcConnectionManager
        Singleton providing JWT and shared ``httpx`` client.
    """

    def __init__(
        self,
        settings: BmcSettings | None = None,
        connection_manager: BmcConnectionManager | None = None,
    ) -> None:
        self._settings = settings or BmcSettings()
        self._manager = connection_manager or BmcConnectionManager.instance(self._settings)

    @staticmethod
    def entry_path(form_name: str, request_id: str | None = None) -> str:
        """Build a URL-encoded AR entry path for a form and optional entry id.

        Parameters
        ----------
        form_name : str
            BMC form name segment in the path.
        request_id : str | None, optional
            AR Request ID for a single-entry resource, by default ``None``.

        Returns
        -------
        str
            Relative path under ``API_PATH_ARSYS_ENTRY_PREFIX``.
        """

        base = f"{API_PATH_ARSYS_ENTRY_PREFIX}/{quote(form_name, safe='')}"
        if request_id is not None:
            return f"{base}/{quote(request_id, safe='')}"
        return base

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, JsonValue] | None = None,
        data: dict[str, str] | None = None,
        files: HttpxMultipartParts | None = None,
    ) -> httpx.Response:
        """Execute an authenticated HTTP request with one 401 retry.

        Parameters
        ----------
        method : str
            HTTP verb (e.g. ``GET``, ``POST``).
        path : str
            Relative AR API path.
        params : dict[str, str] | None, optional
            Query string parameters, by default ``None``.
        json_body : dict[str, JsonValue] | None, optional
            JSON request body, by default ``None``.
        data : dict[str, str] | None, optional
            Form fields for multipart requests, by default ``None``.
        files : HttpxMultipartParts | None, optional
            Multipart parts for httpx (transport), by default ``None``.

        Returns
        -------
        httpx.Response
            Successful response after ``raise_for_status``.

        Raises
        ------
        httpx.HTTPStatusError
            When the status is not successful after retry.
        """
        client = await self._manager.get_client()
        headers = self._manager.auth_headers()
        if files is not None:
            headers = {
                header_name: header_value
                for header_name, header_value in headers.items()
                if header_name.lower() != "content-type"
            }

        async def _do_request() -> httpx.Response:
            return await client.request(
                method,
                path,
                params=params,
                json=json_body,
                data=data,
                files=files,
                headers=headers,
            )

        response = await _do_request()
        if response.status_code == HTTPStatus.UNAUTHORIZED:
            await self._manager.invalidate_and_refresh()
            response = await _do_request()
        logger.debug("BMC response status %s for %s %s", response.status_code, method, path)
        if logger.isEnabledFor(logging.DEBUG) and response.content:
            body_text = self.format_http_response_body(response)
            if body_text:
                snippet = body_text[:512]
                logger.debug("BMC response body (truncated): %s", snippet)
        response.raise_for_status()
        return response

    @staticmethod
    def message_for_status(code: int) -> str:
        """Return the user-facing error message for an HTTP status code.

        Parameters
        ----------
        code : int
            HTTP status code from the BMC API response.

        Returns
        -------
        str
            Mapped message from ``USER_ERROR_MESSAGES``, or a generic fallback.
        """
        return USER_ERROR_MESSAGES.get(
            code,
            f"Error: La API de BMC respondió con estado {code}.",
        )

    @staticmethod
    def format_http_response_body(response: httpx.Response) -> str | None:
        """Serialize the BMC HTTP error body for MCP tool output.

        Parameters
        ----------
        response : httpx.Response
            HTTP response from a failed BMC call.

        Returns
        -------
        str | None
            JSON or plain-text body when non-empty; otherwise ``None``.
        """
        if not response.content:
            return None
        try:
            body = response.json()
        except json.JSONDecodeError:
            text = response.text.strip()
            return text if text else None
        return json.dumps(body, ensure_ascii=False)

    @staticmethod
    def message_for_http_error(response: httpx.Response) -> str:
        """Build the MCP tool error message from an HTTP error response.

        Parameters
        ----------
        response : httpx.Response
            Failed BMC HTTP response.

        Returns
        -------
        str
            Serialized API body when present; otherwise a status-based fallback.
        """
        api_body = BmcClient.format_http_response_body(response)
        if api_body:
            return api_body
        return BmcClient.message_for_status(response.status_code)

    def _raise_from_httpx(self, exc: BaseException, *, method: str, path: str) -> None:
        """Map httpx or JSON errors to ``MCPClientError`` with user messages.

        Parameters
        ----------
        exc : BaseException
            Original exception from the HTTP layer or JSON parsing.
        method : str
            HTTP verb used in the failed call (for logging).
        path : str
            Relative path used in the failed call (for logging).

        Raises
        ------
        MCPClientError
            Always raised; never returns normally.
        """
        if isinstance(exc, httpx.HTTPStatusError):
            code = exc.response.status_code
            logger.debug("BMC HTTP error %s %s -> %s", method, path, code)
            raise MCPClientError(
                self.message_for_http_error(exc.response),
                status_code=code,
            ) from exc
        if isinstance(exc, httpx.TimeoutException):
            raise MCPClientError(USER_ERROR_MESSAGE_TIMEOUT, status_code=None) from exc
        if isinstance(exc, httpx.RequestError):
            raise MCPClientError(USER_ERROR_MESSAGE_NETWORK, status_code=None) from exc
        if isinstance(exc, json.JSONDecodeError):
            raise MCPClientError(USER_ERROR_MESSAGE_INVALID_JSON, status_code=None) from exc
        logger.exception("Unexpected BMC API error %s %s", method, path)
        raise MCPClientError(USER_ERROR_MESSAGE_UNEXPECTED, status_code=None) from exc

    async def get_json(self, path: str, *, params: dict[str, str] | None = None) -> JsonValue:
        """Perform HTTP GET and parse the JSON response body.

        Parameters
        ----------
        path : str
            Relative AR API path.
        params : dict[str, str] | None, optional
            Query string parameters, by default ``None``.

        Returns
        -------
        JsonValue
            Parsed JSON body.

        Raises
        ------
        MCPClientError
            On HTTP, network, timeout, or JSON errors.
        """
        logger.debug("BMC GET %s", path)
        try:
            response = await self._request_with_retry("GET", path, params=params)
            return cast("JsonValue", response.json())
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            self._raise_from_httpx(exc, method="GET", path=path)
            raise AssertionError("unreachable") from exc

    async def post_json(
        self,
        path: str,
        *,
        json_body: dict[str, JsonValue],
        params: dict[str, str] | None = None,
    ) -> tuple[JsonValue, str]:
        """Perform HTTP POST with a JSON body.

        Parameters
        ----------
        path : str
            Relative AR API path.
        json_body : dict[str, JsonValue]
            JSON request body.
        params : dict[str, str] | None, optional
            Query string parameters, by default ``None``.

        Returns
        -------
        tuple[JsonValue, str]
            Parsed JSON body and ``Location`` header value.

        Raises
        ------
        MCPClientError
            On HTTP, network, timeout, or JSON errors.
        """
        logger.debug("BMC POST %s", path)
        try:
            response = await self._request_with_retry(
                "POST",
                path,
                params=params,
                json_body=json_body,
            )
            location = response.headers.get("Location", "")
            try:
                body: JsonValue = response.json()
            except json.JSONDecodeError as exc:
                self._raise_from_httpx(exc, method="POST", path=path)
                raise AssertionError("unreachable") from exc
            return body, location
        except httpx.HTTPError as exc:
            self._raise_from_httpx(exc, method="POST", path=path)
            raise AssertionError("unreachable") from exc

    async def put_json(self, path: str, *, json_body: dict[str, JsonValue]) -> JsonValue:
        """Perform HTTP PUT with a JSON body.

        Parameters
        ----------
        path : str
            Relative AR API path.
        json_body : dict[str, JsonValue]
            JSON request body.

        Returns
        -------
        JsonValue
            Parsed JSON body, or empty dict when the response has no content.

        Raises
        ------
        MCPClientError
            On HTTP, network, timeout, or JSON errors.
        """
        logger.debug("BMC PUT %s", path)
        try:
            response = await self._request_with_retry("PUT", path, json_body=json_body)
            if not response.content:
                return {}
            return cast("JsonValue", response.json())
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            self._raise_from_httpx(exc, method="PUT", path=path)
            raise AssertionError("unreachable") from exc

    async def post_multipart(
        self,
        path: str,
        *,
        body: WorkInfoMultipartBody,
    ) -> JsonValue:
        """Perform HTTP POST with multipart form data.

        Parameters
        ----------
        path : str
            Relative AR API path.
        body : WorkInfoMultipartBody
            WorkInfo multipart payload (``entry`` JSON and optional attach).

        Returns
        -------
        JsonValue
            Parsed JSON body when present; otherwise empty dict.

        Raises
        ------
        MCPClientError
            On HTTP, network, timeout, or JSON errors.
        """
        logger.debug("BMC POST multipart %s", path)
        try:
            response = await self._request_with_retry(
                "POST",
                path,
                files=body.as_httpx_files(),
            )
            if not response.content:
                return {}
            return cast("JsonValue", response.json())
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            self._raise_from_httpx(exc, method="POST", path=path)
            raise AssertionError("unreachable") from exc

    async def search_work_order(self, work_order_id: str) -> BmcEntryListResponse:
        """Search work orders by Work Order ID.

        Parameters
        ----------
        work_order_id : str
            Work Order ID qualification value.

        Returns
        -------
        BmcEntryListResponse
            Parsed list/search response.

        Raises
        ------
        MCPClientError
            On HTTP or parse errors.
        """
        qualification = ArQueryBuilder.equals(AR_FIELD_WORK_ORDER_ID, work_order_id)
        path = self.entry_path(self._settings.form_wo_query)
        payload = await self.get_json(path, params={"q": qualification})
        return parse_entry_list(payload)

    async def search_incident(self, incident_number: str) -> BmcEntryListResponse:
        """Search incidents by Incident Number.

        Parameters
        ----------
        incident_number : str
            Incident Number qualification value.

        Returns
        -------
        BmcEntryListResponse
            Parsed list/search response.

        Raises
        ------
        MCPClientError
            On HTTP or parse errors.
        """
        qualification = ArQueryBuilder.equals(AR_FIELD_INCIDENT_NUMBER, incident_number)
        path = self.entry_path(self._settings.form_incident_query)
        payload = await self.get_json(path, params={"q": qualification})
        return parse_entry_list(payload)

    async def search_work_orders_by_email(self, email: str) -> BmcEntryListResponse:
        """Search work orders by requester email (``Customer Internet E-mail``).

        Parameters
        ----------
        email : str
            Requester email, as originally passed to ``reporter_email`` at creation.

        Returns
        -------
        BmcEntryListResponse
            Parsed list/search response; may contain any number of entries.

        Raises
        ------
        MCPClientError
            On HTTP or parse errors.
        """
        qualification = ArQueryBuilder.equals(AR_FIELD_WO_CUSTOMER_EMAIL, email)
        path = self.entry_path(self._settings.form_wo_query)
        payload = await self.get_json(path, params={"q": qualification})
        return parse_entry_list(payload)

    async def search_incidents_by_email(self, email: str) -> BmcEntryListResponse:
        """Search incidents by requester email (``Internet E-mail``).

        Parameters
        ----------
        email : str
            Requester email, as originally passed to ``reporter_email`` at creation.

        Returns
        -------
        BmcEntryListResponse
            Parsed list/search response; may contain any number of entries.

        Raises
        ------
        MCPClientError
            On HTTP or parse errors.
        """
        qualification = ArQueryBuilder.equals(AR_FIELD_INCIDENT_REPORTER_EMAIL, email)
        path = self.entry_path(self._settings.form_incident_query)
        payload = await self.get_json(path, params={"q": qualification})
        return parse_entry_list(payload)

    async def search_person_by_email(self, email: str) -> BmcEntryListResponse:
        """Search ``CTM:People`` by ``Internet E-mail``.

        Parameters
        ----------
        email : str
            ``Internet E-mail`` qualification value.

        Returns
        -------
        BmcEntryListResponse
            Parsed list/search response. May contain 0, 1, or more entries —
            ``Internet E-mail`` is not a unique key in BMC's People table.

        Raises
        ------
        MCPClientError
            On HTTP or parse errors.
        """
        qualification = ArQueryBuilder.equals(AR_FIELD_PEOPLE_EMAIL, email)
        path = self.entry_path(self._settings.form_people_query)
        fields = (
            f"values({AR_FIELD_PEOPLE_LOGIN_ID},{AR_FIELD_PEOPLE_FIRST_NAME},"
            f"{AR_FIELD_PEOPLE_LAST_NAME},{AR_FIELD_PEOPLE_EMAIL},{AR_FIELD_PEOPLE_STATUS})"
        )
        payload = await self.get_json(path, params={"q": qualification, "fields": fields})
        return parse_entry_list(payload)

    async def create_work_order_entry(
        self,
        json_body: dict[str, JsonValue],
    ) -> BmcCreateEntryResponse:
        """Create a work order entry via POST.

        Parameters
        ----------
        json_body : dict[str, JsonValue]
            Wrapped ``values`` body for create form.

        Returns
        -------
        BmcCreateEntryResponse
            Parsed create response with ids.

        Raises
        ------
        MCPClientError
            On HTTP or parse errors.
        """
        path = self.entry_path(self._settings.form_wo_create)
        params = {"fields": f"values({AR_FIELD_WORK_ORDER_ID_RESPONSE},{AR_FIELD_REQUEST_ID})"}
        body, location = await self.post_json(path, json_body=json_body, params=params)
        return parse_create_response(body, location)

    async def create_incident_entry(
        self,
        json_body: dict[str, JsonValue],
    ) -> BmcCreateEntryResponse:
        """Create an incident entry via POST.

        Parameters
        ----------
        json_body : dict[str, JsonValue]
            Wrapped ``values`` body for create form.

        Returns
        -------
        BmcCreateEntryResponse
            Parsed create response with ids.

        Raises
        ------
        MCPClientError
            On HTTP or parse errors.
        """
        path = self.entry_path(self._settings.form_incident_create)
        params = {"fields": f"values({AR_FIELD_INCIDENT_NUMBER},Description)"}
        body, location = await self.post_json(path, json_body=json_body, params=params)
        return parse_create_response(body, location)

    async def update_work_order(
        self,
        request_id: str,
        json_body: dict[str, JsonValue],
    ) -> JsonValue:
        """Update a work order by Request ID.

        Parameters
        ----------
        request_id : str
            AR Request ID from a prior search.
        json_body : dict[str, JsonValue]
            Wrapped ``values`` body for update.

        Returns
        -------
        JsonValue
            Parsed PUT response body.

        Raises
        ------
        MCPClientError
            On HTTP errors.
        """
        path = self.entry_path(self._settings.form_wo_update, request_id)
        logger.info("json_body: %s", json_body)
        return await self.put_json(path, json_body=json_body)

    async def update_incident(
        self,
        request_id: str,
        json_body: dict[str, JsonValue],
    ) -> JsonValue:
        """Update an incident by Request ID.

        Parameters
        ----------
        request_id : str
            AR Request ID from a prior search.
        json_body : dict[str, JsonValue]
            Wrapped ``values`` body for update.

        Returns
        -------
        JsonValue
            Parsed PUT response body.

        Raises
        ------
        MCPClientError
            On HTTP errors.
        """
        path = self.entry_path(self._settings.form_incident_query, request_id)
        return await self.put_json(path, json_body=json_body)

    async def post_work_info(self, body: WorkInfoMultipartBody) -> JsonValue:
        """Post a work log entry (note or note with attachment).

        Parameters
        ----------
        body : WorkInfoMultipartBody
            Multipart payload for ``WOI:WorkInfo`` (always includes ``entry`` JSON).

        Returns
        -------
        JsonValue
            Parsed response when present.

        Raises
        ------
        MCPClientError
            On HTTP errors.
        """
        path = self.entry_path(self._settings.form_work_info)
        return await self.post_multipart(path, body=body)

    async def post_incident_work_log(self, body: WorkInfoMultipartBody) -> JsonValue:
        """Post a work log entry for an incident (note or note with attachment).

        Parameters
        ----------
        body : WorkInfoMultipartBody
            Multipart payload for ``HPD:WorkLog`` (always includes ``entry`` JSON).

        Returns
        -------
        JsonValue
            Parsed response when present.

        Raises
        ------
        MCPClientError
            On HTTP errors.
        """
        path = self.entry_path(self._settings.form_incident_work_log)
        return await self.post_multipart(path, body=body)

    async def health_ping(self) -> None:
        """Run a lightweight authenticated request to verify session health.

        A 404 on this search counts as healthy (empty result, not an auth or
        connectivity failure).

        Raises
        ------
        MCPClientError
            On auth or unexpected HTTP errors.
        """
        try:
            await self.search_work_order("WO0000000000000")
        except MCPClientError as exc:
            if exc.status_code != HTTPStatus.NOT_FOUND:
                raise
