"""Build AR System qualification strings for GET entry queries."""


class ArQueryBuilder:
    """Escape and format AR query parameters for BMC list/search GET requests."""

    @staticmethod
    def escape_value(value: str) -> str:
        """Escape backslashes and double quotes inside AR field values.

        Parameters
        ----------
        value : str
            Raw field value before embedding in a qualification string.

        Returns
        -------
        str
            Value safe to place inside double quotes in an AR qualification.
        """
        return value.replace('\\', '\\\\').replace('"', '\\"')

    @classmethod
    def equals(cls, field_name: str, value: str) -> str:
        """Build an AR qualification fragment for equality on one field.

        Parameters
        ----------
        field_name : str
            AR field name (unquoted in the API string).
        value : str
            Raw field value; embedded quotes are escaped.

        Returns
        -------
        str
            Fragment of the form ``'Field'="value"``.
        """
        escaped = cls.escape_value(value)
        return f'\'{field_name}\'="{escaped}"'
