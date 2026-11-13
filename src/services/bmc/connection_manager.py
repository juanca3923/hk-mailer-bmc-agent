"""Singleton BMC session: JWT login, cookie jar, and background refresh."""

import asyncio
import logging
from typing import ClassVar

import httpx

from config.bmc_settings import BmcSettings
from constants.bmc import (
    API_PATH_JWT_LOGIN,
    HEADER_AUTHORIZATION_PREFIX,
    HEADER_CONTENT_TYPE_JSON,
    HEADER_X_REQUESTED_BY,
    MIN_REFRESH_LOOP_SECONDS,
    USER_ERROR_MESSAGE_LOGIN_FAILED,
)
from exception.mcp import MCPLoginError

logger = logging.getLogger(__name__)


class BmcConnectionManager:
    """Manage one authenticated ``httpx.AsyncClient`` per MCP process.

    A process-wide singleton holds the JWT token, cookie jar, and background
    refresh loop.

    Attributes
    ----------
    _settings : BmcSettings
        BMC credentials and refresh timing.
    _session_lock : asyncio.Lock
        Serializes login and token updates.
    _token : str
        Current JWT bearer token.
    _client : httpx.AsyncClient | None
        Shared HTTP client after ``start``.
    _refresh_task : asyncio.Task[None] | None
        Background JWT refresh task.
    _stopped : bool
        Flag to stop the refresh loop on shutdown.
    """

    _instance: ClassVar['BmcConnectionManager | None'] = None

    def __init__(self, settings: BmcSettings | None = None) -> None:
        self._settings = settings or BmcSettings()
        self._session_lock = asyncio.Lock()
        self._token: str = ''
        self._client: httpx.AsyncClient | None = None
        self._refresh_task: asyncio.Task[None] | None = None
        self._stopped = False

    @classmethod
    def instance(cls, settings: BmcSettings | None = None) -> 'BmcConnectionManager':
        """Return the process-wide singleton, creating it on first use.

        Parameters
        ----------
        settings : BmcSettings | None, optional
            Settings used only when creating the singleton, by default ``None``.

        Returns
        -------
        BmcConnectionManager
            Shared connection manager instance.
        """
        if cls._instance is None:
            cls._instance = cls(settings)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Clear the singleton instance (for tests only)."""
        cls._instance = None

    async def start(self) -> None:
        """Log in immediately and start the background JWT refresh loop.

        Raises
        ------
        MCPLoginError
            When JWT login fails.
        """
        self._stopped = False
        if self._client is None:
            self._client = self._build_client()
        await self.refresh_session()
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._refresh_loop())
        logger.info('BMC connection manager started')

    def _build_client(self) -> httpx.AsyncClient:
        timeout = httpx.Timeout(self._settings.http_timeout_seconds)
        return httpx.AsyncClient(
            base_url=self._settings.base_url,
            timeout=timeout,
            follow_redirects=True,
        )

    async def refresh_session(self) -> None:
        """Perform JWT login and store the token and cookies.

        Raises
        ------
        MCPLoginError
            On HTTP failure or empty token body.
        """
        async with self._session_lock:
            if self._client is None:
                self._client = self._build_client()
            client = self._client
            try:
                response = await client.post(
                    API_PATH_JWT_LOGIN,
                    data={
                        'username': self._settings.username,
                        'password': self._settings.password,
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.error('BMC login failed: %s', type(exc).__name__)
                raise MCPLoginError(USER_ERROR_MESSAGE_LOGIN_FAILED) from exc

            token = response.text.strip()
            if not token:
                logger.error('BMC login returned empty JWT body')
                raise MCPLoginError(USER_ERROR_MESSAGE_LOGIN_FAILED)

            self._token = token
            logger.info('BMC JWT session refreshed successfully')

    async def _refresh_loop(self) -> None:
        interval = self._refresh_interval_seconds()
        logger.info('BMC JWT background refresh every %s seconds', interval)
        while not self._stopped:
            try:
                await asyncio.sleep(interval)
                if self._stopped:
                    break
                await self.refresh_session()
            except asyncio.CancelledError:
                break
            except MCPLoginError:
                logger.exception('Background BMC JWT refresh failed')
            except httpx.HTTPError:
                logger.exception('Background BMC JWT refresh HTTP error')

    def _refresh_interval_seconds(self) -> int:
        fixed = self._settings.jwt_refresh_interval_seconds
        if fixed > 0:
            return max(fixed, MIN_REFRESH_LOOP_SECONDS)
        computed = self._settings.jwt_ttl_seconds - self._settings.jwt_refresh_margin_seconds
        return max(computed, MIN_REFRESH_LOOP_SECONDS)

    async def stop(self) -> None:
        """Cancel the refresh task and close the HTTP client."""
        self._stopped = True
        if self._refresh_task is not None:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self._refresh_task = None
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        logger.info('BMC connection manager stopped')

    async def get_client(self) -> httpx.AsyncClient:
        """Return the shared HTTP client.

        Returns
        -------
        httpx.AsyncClient
            Client created during ``start``.

        Raises
        ------
        RuntimeError
            If ``start`` was not called.
        """
        if self._client is None:
            msg = 'BmcConnectionManager is not started'
            raise RuntimeError(msg)
        return self._client

    def auth_headers(self) -> dict[str, str]:
        """Build headers required on authenticated BMC requests.

        Returns
        -------
        dict[str, str]
            Authorization, Content-Type, and X-Requested-By headers.
        """
        return {
            'Authorization': f'{HEADER_AUTHORIZATION_PREFIX} {self._token}',
            'Content-Type': HEADER_CONTENT_TYPE_JSON,
            'X-Requested-By': HEADER_X_REQUESTED_BY,
        }

    async def invalidate_and_refresh(self) -> None:
        """Re-login after HTTP 401 (reactive session refresh).

        Raises
        ------
        MCPLoginError
            When refresh login fails.
        """
        logger.warning('BMC session invalidated; refreshing JWT')
        await self.refresh_session()
