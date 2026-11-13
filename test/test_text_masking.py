"""Unit tests for the log masking helpers."""

from commons.text.masking import mask_email


def test_mask_email_keeps_first_char_and_domain() -> None:
    assert mask_email('juan.perez@henkia.com') == 'j***@henkia.com'


def test_mask_email_strips_whitespace() -> None:
    assert mask_email('  ana@x.co ') == 'a***@x.co'


def test_mask_email_hides_values_that_are_not_addresses() -> None:
    assert mask_email('no-es-correo') == '***'
    assert mask_email('@dominio.com') == '***'
    assert mask_email('') == '***'
