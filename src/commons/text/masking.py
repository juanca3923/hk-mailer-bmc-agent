"""Pure helpers that hide personal data before it is written to logs."""


def mask_email(address: str) -> str:
    """Mask the local part of an email address, keeping its first character and domain.

    Parameters
    ----------
    address : str
        Email address (``user@domain``); surrounding whitespace is ignored.

    Returns
    -------
    str
        ``u***@domain``; ``***`` when the value does not look like an address.
    """
    local, separator, domain = address.strip().partition('@')
    if not separator or not local or not domain:
        return '***'
    return f'{local[0]}***@{domain}'
