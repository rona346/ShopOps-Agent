"""
Supabase client and authentication foundation for ShopOps Agent.
Provides:
1. Supabase JWT signature and claims verification.
2. Lightweight, fail-closed PostgREST database client for privileged server-side operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import httpx
import jwt
from pydantic import BaseModel

from app.core.config import settings


class SupabaseError(Exception):
    """Base exception for Supabase operations."""
    pass


class SupabaseUnavailableError(SupabaseError):
    """Raised when Supabase credentials or services are unconfigured or unreachable."""
    pass


class SupabaseQueryError(SupabaseError):
    """Raised when a PostgREST query fails."""
    def __init__(self, message: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


def is_supabase_configured() -> bool:
    """Check whether Supabase URL and credentials are provided in configuration."""
    url = (settings.SUPABASE_URL or "").strip()
    key = (settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY or "").strip()
    secret = (settings.SUPABASE_JWT_SECRET or "").strip()

    if url and (key or secret):
        return True
    if secret:
        return True
    return False


def verify_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Verify a Supabase-issued JWT and extract authenticated claims.
    Supported verification strategies:
    1. Local cryptographic HS256 verification using SUPABASE_JWT_SECRET (fastest, offline).
    2. Supabase Auth API verification via {SUPABASE_URL}/auth/v1/user (universal fallback).

    Validates signature, expiration (exp), audience (aud="authenticated"),
    and extracts subject (uid) and email.
    """
    token = token.strip() if token else ""
    if not token:
        raise jwt.InvalidTokenError("Token is empty")

    jwt_secret = (settings.SUPABASE_JWT_SECRET or "").strip()
    supabase_url = (settings.SUPABASE_URL or "").strip()
    api_key = (settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY or "").strip()

    # Strategy 1: Local cryptographic verification if JWT Secret is configured
    if jwt_secret:
        try:
            decode_options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True,
            }
            payload = jwt.decode(
                token,
                key=jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options=decode_options,
            )
            uid = payload.get("sub") or payload.get("id") or ""
            email = payload.get("email")
            if not uid:
                raise jwt.InvalidTokenError("Token missing 'sub' claim")
            return {
                "uid": uid,
                "email": email,
                "role": payload.get("role", "authenticated"),
                "payload": payload,
            }
        except jwt.ExpiredSignatureError:
            raise
        except jwt.InvalidTokenError:
            # If local secret fails and URL is also configured, try Auth endpoint as secondary
            if not supabase_url:
                raise

    # Strategy 2: Remote verification against Supabase Auth API
    if supabase_url:
        auth_user_url = f"{supabase_url.rstrip('/')}/auth/v1/user"
        headers = {
            "Authorization": f"Bearer {token}",
            "apikey": api_key or "anon",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(auth_user_url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    uid = data.get("id", "")
                    email = data.get("email")
                    if not uid:
                        raise jwt.InvalidTokenError("Supabase user response missing 'id'")
                    return {
                        "uid": uid,
                        "email": email,
                        "role": data.get("role", "authenticated"),
                        "payload": data,
                    }
                elif res.status_code in (401, 403):
                    body = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
                    msg = body.get("message") or body.get("error_description") or body.get("msg") or "Token is invalid"
                    if "expired" in msg.lower():
                        raise jwt.ExpiredSignatureError("Authentication token has expired")
                    raise jwt.InvalidTokenError(f"Supabase rejected token: {msg}")
                else:
                    raise SupabaseError(f"Unexpected Supabase auth response: HTTP {res.status_code}")
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            raise
        except Exception as exc:
            raise SupabaseError(f"Failed to communicate with Supabase Auth: {str(exc)}") from exc

    raise SupabaseUnavailableError("Neither SUPABASE_JWT_SECRET nor SUPABASE_URL is configured.")


class SupabaseDatabaseClient:
    """
    Lightweight PostgREST client for direct, privileged PostgreSQL operations.
    Connects with service_role privileges, bypassing RLS as the authoritative backend orchestrator.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        service_role_key: Optional[str] = None,
        timeout: float = 10.0,
    ):
        url = base_url or settings.SUPABASE_URL or ""
        self.base_url = f"{url.rstrip('/')}/rest/v1"
        self.key = service_role_key or settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY or ""
        self.timeout = timeout

    def _get_headers(self, prefer: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a row and return the inserted record."""
        url = f"{self.base_url}/{table}"
        headers = self._get_headers(prefer="return=representation")
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(url, json=data, headers=headers)
            if res.status_code in (200, 201):
                results = res.json()
                if isinstance(results, list) and results:
                    return results[0]
                return results
            self._handle_error(res, table=table, op="insert")

    def get_by_id(self, table: str, row_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single row by ID."""
        url = f"{self.base_url}/{table}"
        params = {"id": f"eq.{row_id}", "select": "*"}
        headers = self._get_headers()
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(url, params=params, headers=headers)
            if res.status_code == 200:
                results = res.json()
                if isinstance(results, list) and results:
                    return results[0]
                return None
            self._handle_error(res, table=table, op="get_by_id")

    def select(
        self,
        table: str,
        params: Optional[Dict[str, str]] = None,
        limit: int = 50,
        offset: int = 0,
        order: Optional[str] = "created_at.desc",
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Query rows with pagination and exact total count from Content-Range header."""
        url = f"{self.base_url}/{table}"
        query_params: Dict[str, str] = {"select": "*", "limit": str(limit), "offset": str(offset)}
        if order:
            query_params["order"] = order
        if params:
            query_params.update(params)

        headers = self._get_headers(prefer="count=exact")
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(url, params=query_params, headers=headers)
            if res.status_code == 200:
                rows = res.json()
                total = len(rows)
                # Parse Content-Range header (e.g., '0-9/42' or '*/42')
                cr = res.headers.get("content-range", "")
                if "/" in cr:
                    try:
                        total = int(cr.split("/")[-1])
                    except (ValueError, IndexError):
                        pass
                return rows, total
            self._handle_error(res, table=table, op="select")

    def update(self, table: str, row_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a row by ID and return the updated record."""
        url = f"{self.base_url}/{table}"
        params = {"id": f"eq.{row_id}"}
        headers = self._get_headers(prefer="return=representation")
        with httpx.Client(timeout=self.timeout) as client:
            res = client.patch(url, params=params, json=data, headers=headers)
            if res.status_code == 200:
                results = res.json()
                if isinstance(results, list) and results:
                    return results[0]
                return results
            self._handle_error(res, table=table, op="update")

    def delete(self, table: str, row_id: str) -> None:
        """Delete a row by ID."""
        url = f"{self.base_url}/{table}"
        params = {"id": f"eq.{row_id}"}
        headers = self._get_headers()
        with httpx.Client(timeout=self.timeout) as client:
            res = client.delete(url, params=params, headers=headers)
            if res.status_code in (200, 204):
                return
            self._handle_error(res, table=table, op="delete")

    def _handle_error(self, res: httpx.Response, table: str, op: str) -> None:
        status_code = res.status_code
        try:
            body = res.json()
        except Exception:
            body = {"message": res.text}

        code = str(body.get("code", ""))
        message = str(body.get("message", ""))
        details = str(body.get("details", ""))

        raise SupabaseQueryError(
            f"Supabase {op} failed on table '{table}' (HTTP {status_code}, code {code}): {message}. {details}",
            status_code=status_code,
            details=body,
        )


_client_instance: Optional[SupabaseDatabaseClient] = None


def get_supabase_client() -> SupabaseDatabaseClient:
    """Retrieve singleton instance of privileged Supabase database client."""
    global _client_instance
    if not is_supabase_configured():
        raise SupabaseUnavailableError(
            "Supabase is not configured. Please set SUPABASE_URL and "
            "SUPABASE_SERVICE_ROLE_KEY in backend/.env."
        )
    if _client_instance is None:
        _client_instance = SupabaseDatabaseClient()
    return _client_instance
