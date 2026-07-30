"""Unit tests for pure ticket write guards (status and ownership)."""

from bmc.libs.helpers.ticket_guards import require_not_closed, require_submitter


def test_require_not_closed_allows_open_status() -> None:
    assert require_not_closed('In Progress') is None


def test_require_not_closed_rejects_closed() -> None:
    result = require_not_closed('Closed')
    assert result is not None
    assert result.success is False


def test_require_submitter_allows_exact_match() -> None:
    assert require_submitter('svc_mosaico', 'svc_mosaico') is None


def test_require_submitter_rejects_mismatch() -> None:
    result = require_submitter('otro_usuario', 'svc_mosaico')
    assert result is not None
    assert result.success is False
    assert 'otro_usuario' in result.message
