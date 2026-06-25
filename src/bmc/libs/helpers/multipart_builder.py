"""Build multipart form data for ``WOI:WorkInfo`` entries."""

import json
from pathlib import Path

from pydantic import BaseModel

from bmc.libs.constants import (
    MULTIPART_ATTACH_PREFIX,
    MULTIPART_ENTRY_CONTENT_TYPE,
    MULTIPART_PART_ENTRY,
    WORK_LOG_ATTACHMENT_FIELD,
)
from bmc.libs.helpers.entry_values_mapper import EntryValuesMapper

# httpx ``files=`` mapping: field name -> (filename, content, content_type)
HttpxMultipartPart = tuple[str | None, bytes | str, str | None]
HttpxMultipartParts = dict[str, HttpxMultipartPart]


class WorkInfoMultipartBody:
    """Multipart payload for BMC ``WOI:WorkInfo`` POST.

    Always contains the ``entry`` form part (JSON ``values``). May also contain
    an ``attach-...`` part when a binary attachment is included. This is not a
    "file upload only" object: notes without attachment still use multipart.

    Attributes
    ----------
    parts : HttpxMultipartParts
        Internal part map passed to httpx at transport layer.
    """

    __slots__ = ('parts',)

    def __init__(self, parts: HttpxMultipartParts) -> None:
        self.parts = parts

    def as_httpx_files(self) -> HttpxMultipartParts:
        """Return the part map for httpx ``files=`` (HTTP transport only).

        Returns
        -------
        HttpxMultipartParts
            Part name to (filename, content, content_type) tuples.
        """
        return self.parts

    @property
    def has_binary_attachment(self) -> bool:
        """Whether a binary attach part is present in addition to ``entry``."""
        return len(self.parts) > 1


class AttachmentPart:
    """Binary attachment for work log multipart upload.

    Attributes
    ----------
    filename : str
        Original file name sent to BMC.
    content : bytes
        Raw file bytes.
    content_type : str
        MIME type for the attachment part.
    """

    def __init__(self, filename: str, content: bytes, content_type: str = 'application/octet-stream') -> None:
        self.filename = filename
        self.content = content
        self.content_type = content_type

    @classmethod
    def from_path(cls, path: Path) -> 'AttachmentPart':
        """Load attachment bytes from a local file path.

        Parameters
        ----------
        path : Path
            Path to an existing file on disk.

        Returns
        -------
        AttachmentPart
            Part ready for ``MultipartBuilder.build``.

        Raises
        ------
        OSError
            If the file cannot be read.
        """
        data = path.read_bytes()
        return cls(filename=path.name, content=data)


class MultipartBuilder:
    """Construct multipart parts for BMC WorkInfo POST."""

    @staticmethod
    def build(
        values_model: BaseModel,
        attachment: AttachmentPart | None = None,
    ) -> WorkInfoMultipartBody:
        """Build multipart body for a WorkInfo create (note with optional attach).

        BMC expects ``multipart/form-data`` with an ``entry`` part (JSON), even when
        there is no binary attachment.

        Parameters
        ----------
        values_model : BaseModel
            Work log values model (serialized as JSON in the ``entry`` part).
        attachment : AttachmentPart | None, optional
            Optional binary attachment, by default ``None``.

        Returns
        -------
        WorkInfoMultipartBody
            Multipart payload with ``entry`` JSON and optional attach part.
        """
        body = EntryValuesMapper.wrap_entry_body(values_model)
        entry_json = json.dumps(body, ensure_ascii=False)
        parts: HttpxMultipartParts = {
            MULTIPART_PART_ENTRY: (
                None,
                entry_json.encode('utf-8'),
                MULTIPART_ENTRY_CONTENT_TYPE,
            ),
        }
        if attachment is not None:
            part_name = f'{MULTIPART_ATTACH_PREFIX}{WORK_LOG_ATTACHMENT_FIELD}'
            parts[part_name] = (
                attachment.filename,
                attachment.content,
                attachment.content_type,
            )
        return WorkInfoMultipartBody(parts)
