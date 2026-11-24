"""
Authentication and API Security for ShopOps Agent.
Enforces Firebase ID Token verification with fail-closed production guarantees
and isolated development fallback mode.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth
import jwt
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.firebase import get_firebase_app, is_firebase_configured
from app.core.supabase import (
    is_supabase_configured,
    verify_supabase_jwt,
    SupabaseError,
    SupabaseUnavailableError,
)

security = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    """Domain model representing an authenticated store owner."""
    uid: str = Field(..., description="Firebase UID or unique user identifier")
    email: Optional[str] = Field(default=None, description="Authenticated user email")
    role: str = Field(default="owner", description="User role in ShopOps")


def is_dev_auth_enabled() -> bool:
    """
    Check if development fallback authentication is explicitly permitted.
    STRICT SECURITY INVARIANT:
    - Never permitted in production environment, under any circumstance.
    - Requires explicit development or testing environment.
    - Requires ENABLE_DEV_AUTH to be True.
    - Requires non-empty DEV_AUTH_TOKEN.
    """
    env = (settings.ENVIRONMENT or "").strip().lower()
    if env == "production":
        return False
    if env not in ("development", "testing"):
        return False
    if not getattr(settings, "ENABLE_DEV_AUTH", False):
        return False
    if not settings.DEV_AUTH_TOKEN or not settings.DEV_AUTH_TOKEN.strip():
        return False
    return True


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthenticatedUser:
    """
    FastAPI dependency that validates the Bearer token and returns the authenticated user.
    - Production mode fails closed: dev fallback is strictly disabled and missing Firebase rejects requests.
    - If Firebase Admin is configured, verifies the live Firebase ID Token using Google's public keys.
    - If OWNER_EMAIL is configured, enforces that the authenticated email matches the authorized owner.
    - If Firebase Admin is unconfigured and running in explicit development mode, accepts DEV_AUTH_TOKEN.
    - Otherwise, rejects unauthenticated, invalid, or unauthorized requests with HTTP 401 or HTTP 403.
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip() if credentials.credentials else ""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    env = (settings.ENVIRONMENT or "").strip().lower()

    # 1. Primary: Live Supabase Authentication Verification
    if is_supabase_configured():
        try:
            user_info = verify_supabase_jwt(token)
            email = user_info.get("email")

            # Enforce single-owner restriction if OWNER_EMAIL is defined
            if settings.OWNER_EMAIL:
                if not email or email.strip().lower() != settings.OWNER_EMAIL.strip().lower():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"User '{email or 'unknown'}' is not authorized as the store owner.",
                    )

            return AuthenticatedUser(
                uid=user_info.get("uid", ""),
                email=email,
                role="owner",
            )
        except HTTPException:
            raise
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired",
                headers={
                    "WWW-Authenticate": 'Bearer error="invalid_token", error_description="The token has expired"'
                },
            )
        except jwt.InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(exc)}",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            )
        except (SupabaseError, Exception) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Supabase authentication verification failed: {str(exc)}",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            )

    # 2. Secondary / Legacy: Firebase Authentication Verification
    if is_firebase_configured():
        try:
            app = get_firebase_app()
            decoded = auth.verify_id_token(token, app=app)
            email = decoded.get("email")

            # Enforce single-owner hackathon restriction if OWNER_EMAIL is defined
            if settings.OWNER_EMAIL:
                if not email or email.strip().lower() != settings.OWNER_EMAIL.strip().lower():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"User '{email or 'unknown'}' is not authorized as the store owner.",
                    )

            return AuthenticatedUser(
                uid=decoded.get("uid", ""),
                email=email,
                role="owner",
            )
        except HTTPException:
            raise
        except auth.ExpiredIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has expired",
                headers={
                    "WWW-Authenticate": 'Bearer error="invalid_token", error_description="The token has expired"'
                },
            )
        except auth.RevokedIdTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token has been revoked",
                headers={
                    "WWW-Authenticate": 'Bearer error="invalid_token", error_description="The token has been revoked"'
                },
            )
        except (auth.InvalidIdTokenError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(exc)}",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Firebase authentication verification failed: {str(exc)}",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            )

    # 3. Fail Closed in Production if neither Supabase nor Firebase is configured
    if env == "production":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Production mode requires valid Firebase Admin or Supabase configuration. Development fallback authentication is disabled.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    # 4. Explicit Development Mode Fallback
    if is_dev_auth_enabled():
        if token == settings.DEV_AUTH_TOKEN:
            return AuthenticatedUser(
                uid="dev-owner-001",
                email=settings.OWNER_EMAIL or "owner@shopops.local",
                role="owner",
            )

    # 5. Fail Closed: Reject all other tokens as unauthorized
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token. Development fallback is disabled or token did not match.",
        headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
    )
