"""Rutas, cabeceras, cookies, tiempos y partes multipart de la API REST de BMC."""

from __future__ import annotations

from typing import Final

READ_TIMEOUT_SECONDS: Final[float] = 30.0


API_PATH_JWT_LOGIN: Final[str] = "/api/jwt/login"


API_PATH_JWT_LOGOUT: Final[str] = "/api/jwt/logout"


API_PATH_ARSYS_ENTRY_PREFIX: Final[str] = "/api/arsys/v1/entry"


HEADER_CONTENT_TYPE_JSON: Final[str] = "application/json"


HEADER_X_REQUESTED_BY: Final[str] = "XMLHttpRequest"


HEADER_AUTHORIZATION_PREFIX: Final[str] = "AR-JWT"


COOKIE_AR_JWT: Final[str] = "AR-JWT"


WORK_LOG_ATTACHMENT_MARKER: Final[str] = "adjunto"


MULTIPART_PART_ENTRY: Final[str] = "entry"


MULTIPART_ENTRY_CONTENT_TYPE: Final[str] = "application/json"


MULTIPART_ATTACH_PREFIX: Final[str] = "attach-"


MIN_REFRESH_LOOP_SECONDS: Final[int] = 60
