"""
Authentication REST API Endpoints.
Mounted under /api/v1/auth.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.core.firebase import is_firebase_configured

router = APIRouter()


@router.get(
    "/status",
    summary="Check authentication provider configuration status (Public)",
)
def get_auth_status() -> Dict[str, Any]:
    """Public status endpoint to inspect configured authentication mode."""
    firebase_ready = is_firebase_configured()
    return {
        "firebase_configured": firebase_ready,
        "auth_provider": "firebase" if firebase_ready else "development_token",
        "owner_email_configured": bool(settings.OWNER_EMAIL),
        "environment": settings.ENVIRONMENT,
    }


@router.get(
    "/me",
    response_model=AuthenticatedUser,
    summary="Retrieve current authenticated store owner details",
)
def get_current_user_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Returns profile information for the authenticated store owner."""
    return current_user
