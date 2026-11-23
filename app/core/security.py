"""Caller authentication for the department-facing API.

This service is meant to be called by your department's backend (server to server),
not directly by a browser. The backend proves itself with X-API-Key and says which
citizen/user the payment belongs to with X-User-ID.

DEMO ONLY: X-User-ID is trusted because the caller holds the API key. In production,
replace this with verified identity (for example a JWT/OIDC token from your portal).
"""
import hmac
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from app.core.config import Settings, get_settings


def require_api_key(
    x_api_key: str | None = Header(default=None, description="Department backend API key"),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.api_key or not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def current_user(
    x_user_id: str | None = Header(default=None, description="UUID of the citizen/user (demo identity)"),
    _: None = Depends(require_api_key),
) -> str:
    try:
        return str(UUID(x_user_id or ""))
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="A valid X-User-ID (UUID) header is required") from None
