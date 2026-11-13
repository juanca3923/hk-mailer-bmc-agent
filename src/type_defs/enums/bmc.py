"""Conjuntos cerrados de valores de BMC: motivos por los que no se sube un archivo de la carpeta compartida."""

from enum import StrEnum


class StagedSkipReason(StrEnum):
    """Por qué un archivo de la carpeta compartida no se subió al ticket."""

    TOO_LARGE = 'too_large'
    MISSING = 'missing'
    INVALID_NAME = 'invalid_name'
    NOT_ALLOWED = 'not_allowed'
