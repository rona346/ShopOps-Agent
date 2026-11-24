"""
Unit and Integration Tests for Authentication & API Security.
Verifies protected endpoints, 401 responses, token validation, and public routes.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from firebase_admin import auth

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.main import app


class TestAuthAPI(unittest.TestCase):
    """Test suite verifying authentication enforcement and token handling."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    # ----------------------------------------------------
    # Public Endpoint Tests
    # ----------------------------------------------------
    def test_health_endpoint_is_public(self):
        """Verify /health is accessible without any Authorization header."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")

    def test_root_endpoint_is_public(self):
        """Verify / is accessible without any Authorization header."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

    def test_auth_status_endpoint_is_public(self):
        """Verify /api/v1/auth/status is accessible without any Authorization header."""
        res = self.client.get("/api/v1/auth/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("firebase_configured", data)
        self.assertIn("auth_provider", data)

    # ----------------------------------------------------
    # Unauthenticated / Missing Token Tests (HTTP 401)
    # ----------------------------------------------------
    def test_inventory_requires_authentication(self):
        """GET /api/v1/inventory without token must return 401 Unauthorized."""
        res = self.client.get("/api/v1/inventory")
        self.assertEqual(res.status_code, 401)
        self.assertIn("WWW-Authenticate", res.headers)
        self.assertIn("Bearer", res.headers["WWW-Authenticate"])

    def test_agent_insights_requires_authentication(self):
        """GET /api/v1/agent/insights without token must return 401."""
        res = self.client.get("/api/v1/agent/insights")
        self.assertEqual(res.status_code, 401)

    def test_approvals_requires_authentication(self):
        """GET /api/v1/approvals without token must return 401."""
        res = self.client.get("/api/v1/approvals")
        self.assertEqual(res.status_code, 401)

    def test_tasks_requires_authentication(self):
        """GET /api/v1/tasks without token must return 401."""
        res = self.client.get("/api/v1/tasks")
        self.assertEqual(res.status_code, 401)

    def test_auth_me_requires_authentication(self):
        """GET /api/v1/auth/me without token must return 401."""
        res = self.client.get("/api/v1/auth/me")
        self.assertEqual(res.status_code, 401)

    # ----------------------------------------------------
    # Malformed & Invalid Token Tests (HTTP 401)
    # ----------------------------------------------------
    def test_non_bearer_scheme_rejected(self):
        """Non-Bearer auth schemes (e.g., Basic) must return 401."""
        res = self.client.get(
            "/api/v1/inventory",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        self.assertEqual(res.status_code, 401)

    def test_empty_bearer_token_rejected(self):
        """Empty bearer token 'Bearer ' must return 401."""
        res = self.client.get(
            "/api/v1/inventory",
            headers={"Authorization": "Bearer "},
        )
        self.assertEqual(res.status_code, 401)

    def test_invalid_random_token_rejected(self):
        """Invalid random bearer token must return 401."""
        res = self.client.get(
            "/api/v1/inventory",
            headers={"Authorization": "Bearer completely-bogus-token-xyz"},
        )
        self.assertEqual(res.status_code, 401)
        self.assertIn("WWW-Authenticate", res.headers)

    # ----------------------------------------------------
    # Valid Authenticated Access Tests
    # ----------------------------------------------------
    def test_auth_me_with_valid_dev_token(self):
        """GET /api/v1/auth/me with valid DEV_AUTH_TOKEN returns user profile."""
        token = settings.DEV_AUTH_TOKEN
        res = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["role"], "owner")
        self.assertIn("uid", data)

    def test_auth_me_with_dependency_override(self):
        """GET /api/v1/auth/me respects dependency override in isolated tests."""
        test_user = AuthenticatedUser(uid="test_owner_999", email="verified@shopops.com", role="owner")
        app.dependency_overrides[get_current_user] = lambda: test_user

        res = self.client.get("/api/v1/auth/me")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["uid"], "test_owner_999")
        self.assertEqual(data["email"], "verified@shopops.com")

    # ----------------------------------------------------
    # Firebase Token Verification Unit Tests (Mocked)
    # ----------------------------------------------------
    @patch("app.core.auth.is_firebase_configured", return_value=True)
    @patch("app.core.auth.get_firebase_app")
    @patch("firebase_admin.auth.verify_id_token")
    def test_firebase_valid_token_verified(self, mock_verify, mock_get_app, mock_is_config):
        """When Firebase is configured, valid ID token decodes successfully."""
        mock_verify.return_value = {
            "uid": "firebase_uid_123",
            "email": "owner@store.com",
        }
        res = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer mock-valid-firebase-jwt"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["uid"], "firebase_uid_123")
        self.assertEqual(data["email"], "owner@store.com")

    @patch("app.core.auth.is_firebase_configured", return_value=True)
    @patch("app.core.auth.get_firebase_app")
    @patch("firebase_admin.auth.verify_id_token")
    def test_firebase_expired_token_returns_401(self, mock_verify, mock_get_app, mock_is_config):
        """When Firebase reports token expired, returns 401 with appropriate message."""
        mock_verify.side_effect = auth.ExpiredIdTokenError("Token has expired", None)
        res = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer expired-token"},
        )
        self.assertEqual(res.status_code, 401)
        self.assertIn("expired", res.json()["detail"].lower())

    @patch("app.core.auth.is_firebase_configured", return_value=True)
    @patch("app.core.auth.get_firebase_app")
    @patch("firebase_admin.auth.verify_id_token")
    def test_firebase_invalid_token_returns_401(self, mock_verify, mock_get_app, mock_is_config):
        """When Firebase reports token invalid, returns 401."""
        mock_verify.side_effect = auth.InvalidIdTokenError("Invalid token signature")
        res = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer bad-sig-token"},
        )
        self.assertEqual(res.status_code, 401)
        self.assertIn("invalid", res.json()["detail"].lower())

    # ----------------------------------------------------
    # Phase 10: Critical Security Isolation & Fail-Closed Tests
    # ----------------------------------------------------
    def test_dev_fallback_works_only_in_explicit_dev_mode(self):
        """Dev fallback token is accepted ONLY when ENABLE_DEV_AUTH is explicitly True."""
        token = settings.DEV_AUTH_TOKEN

        # 1. When ENABLE_DEV_AUTH is False, dev token is rejected with 401
        with patch.object(settings, "ENABLE_DEV_AUTH", False):
            res = self.client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res.status_code, 401)
            self.assertIn("disabled", res.json()["detail"].lower())

        # 2. When ENVIRONMENT is not development or testing, dev token is rejected with 401
        with patch.object(settings, "ENVIRONMENT", "staging"):
            res = self.client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res.status_code, 401)
            self.assertIn("disabled", res.json()["detail"].lower())

    def test_production_rejects_development_tokens(self):
        """Production environment MUST reject development fallback tokens under all circumstances."""
        token = settings.DEV_AUTH_TOKEN
        with patch.object(settings, "ENVIRONMENT", "production"):
            res = self.client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            self.assertEqual(res.status_code, 401)

    def test_production_missing_firebase_credentials_rejects_protected_requests(self):
        """In production, missing Firebase credentials fails closed and rejects requests with 401."""
        with patch.object(settings, "ENVIRONMENT", "production"):
            with patch("app.core.auth.is_firebase_configured", return_value=False):
                # Attempt with dev token
                res_dev = self.client.get(
                    "/api/v1/inventory",
                    headers={"Authorization": f"Bearer {settings.DEV_AUTH_TOKEN}"},
                )
                self.assertEqual(res_dev.status_code, 401)
                self.assertIn("production mode requires valid firebase admin", res_dev.json()["detail"].lower())

                # Attempt without token
                res_anon = self.client.get("/api/v1/inventory")
                self.assertEqual(res_anon.status_code, 401)

    @patch("app.core.auth.is_firebase_configured", return_value=True)
    @patch("app.core.auth.get_firebase_app")
    @patch("firebase_admin.auth.verify_id_token")
    def test_non_owner_users_cannot_access_owner_only_actions(
        self, mock_verify, mock_get_app, mock_is_config
    ):
        """Verified non-owner accounts receive HTTP 403 Forbidden on protected owner endpoints."""
        with patch.object(settings, "OWNER_EMAIL", "authorized-owner@shopops.com"):
            # 1. Intruder with valid Firebase account but unauthorized email
            mock_verify.return_value = {
                "uid": "intruder_user_456",
                "email": "intruder@unauthorized.com",
            }
            res_intruder = self.client.get(
                "/api/v1/inventory",
                headers={"Authorization": "Bearer valid-firebase-token-intruder"},
            )
            self.assertEqual(res_intruder.status_code, 403)
            self.assertIn("not authorized as the store owner", res_intruder.json()["detail"])

            # 2. Legitimate owner with matching email succeeds
            mock_verify.return_value = {
                "uid": "owner_user_123",
                "email": "authorized-owner@shopops.com",
            }
            res_owner = self.client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer valid-firebase-token-owner"},
            )
            self.assertEqual(res_owner.status_code, 200)
            self.assertEqual(res_owner.json()["email"], "authorized-owner@shopops.com")

    def test_cors_preflight_production_and_preview_domains(self):
        """Verify CORS preflight succeeds for Vercel production and preview domains."""
        # 1. Production domain
        res_prod = self.client.options(
            "/api/v1/tasks?limit=50&offset=0",
            headers={
                "Origin": "https://shop-ops-agent.vercel.app",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        self.assertEqual(res_prod.status_code, 200)
        self.assertEqual(
            res_prod.headers.get("access-control-allow-origin"),
            "https://shop-ops-agent.vercel.app",
        )
        self.assertEqual(res_prod.headers.get("access-control-allow-credentials"), "true")

        # 2. Preview domain
        res_prev = self.client.options(
            "/api/v1/tasks?limit=50&offset=0",
            headers={
                "Origin": "https://shop-ops-agent-avrtm8ir5-guptaronak810-7522s-projects.vercel.app",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        self.assertEqual(res_prev.status_code, 200)
        self.assertEqual(
            res_prev.headers.get("access-control-allow-origin"),
            "https://shop-ops-agent-avrtm8ir5-guptaronak810-7522s-projects.vercel.app",
        )

        # 3. Disallowed origin fails
        res_bad = self.client.options(
            "/api/v1/tasks?limit=50&offset=0",
            headers={
                "Origin": "https://malicious-domain.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        self.assertEqual(res_bad.status_code, 400)
        self.assertNotIn("access-control-allow-origin", res_bad.headers)


if __name__ == "__main__":
    unittest.main()
