"""Request/response shapes for auth and the current-principal endpoint."""

from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

AuthMode = Literal["google", "pseudonymous", "ghost"]

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):  # noqa: UP046 - project supports Python 3.11+
    """The API success envelope from docs/API.md §1."""

    data: T


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=1, max_length=8192)


class PseudoAuthRequest(BaseModel):
    secret: str = Field(min_length=32, max_length=512)
    alias: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_]{3,32}$")
    expiry_days: int | None = None


class AuthResponse(BaseModel):
    alias: str
    token: str
    mode: Literal["google", "pseudonymous"]


class AliasResponse(BaseModel):
    alias: str
    mode: Literal["google", "pseudonymous"]


class MeResponse(BaseModel):
    mode: AuthMode
    alias: str | None
    user_id: str | None
    expiry_days: int
    is_admin: bool
