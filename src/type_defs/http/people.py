"""Pydantic schemas for the sender verification endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PersonVerifyRequest(BaseModel):
    """Request body for ``POST /people/verify``."""

    email: str = Field(..., max_length=254, description='Email address to look up in CTM:People.')

    @field_validator('email')
    @classmethod
    def email_is_not_blank(cls, value: str) -> str:
        """Reject blank emails and return the trimmed value."""
        trimmed = value.strip()
        if not trimmed:
            msg = 'email no puede estar vacío'
            raise ValueError(msg)
        return trimmed


class PersonVerifyResponse(BaseModel):
    """Minimal answer: nothing about the person beyond whether they are a valid origin."""

    exists: bool
    enabled: bool
