"""
Tests for CORS Headers and Error Response Middleware in ShopOps Agent.
Ensures that CORS headers are reliably present on all responses,
including 200, 401, 403, 500 (unhandled server errors), and 502 (Gemini errors).
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.supabase import SupabaseQueryError
from app.services.agent import GeminiServiceError

PROD_ORIGIN = "https://shop-ops-agent.vercel.app"


class TestCorsAndErrorResponses(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_production_origin_configured(self):
        """Verify that the production Vercel origin is explicitly allowed in settings."""
        self.assertIn(PROD_ORIGIN, settings.CORS_ORIGINS)

    def test_cors_preflight_production_origin(self):
        """Verify CORS preflight OPTIONS returns 200 with proper headers for production origin."""
        response = self.client.options(
            "/api/v1/inventory",
            headers={
                "Origin": PROD_ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), PROD_ORIGIN)
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")
        self.assertIn("authorization", response.headers.get("access-control-allow-headers", "").lower())
        # Confirm wildcard is never returned with credentials
        self.assertNotEqual(response.headers.get("access-control-allow-origin"), "*")

    def test_cors_headers_on_200_health(self):
        """Verify GET /health includes CORS headers when Origin is present."""
        response = self.client.get("/health", headers={"Origin": PROD_ORIGIN})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), PROD_ORIGIN)
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_headers_on_401_unauthorized(self):
        """Verify 401 Unauthorized responses retain CORS headers."""
        response = self.client.get("/api/v1/auth/me", headers={"Origin": PROD_ORIGIN})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get("access-control-allow-origin"), PROD_ORIGIN)
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_headers_on_502_gemini_error(self):
        """Verify 502 Bad Gateway (GeminiServiceError) retains CORS headers."""
        @app.get("/api/v1/test-cors-502-route")
        def route_502():
            raise GeminiServiceError("Upstream model unavailable")

        response = self.client.get("/api/v1/test-cors-502-route", headers={"Origin": PROD_ORIGIN})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.headers.get("access-control-allow-origin"), PROD_ORIGIN)
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")
        self.assertIn("Upstream model unavailable", response.json().get("detail", ""))

    def test_cors_headers_on_supabase_query_error(self):
        """Verify PostgREST/Supabase query errors retain CORS headers and return correct status."""
        @app.get("/api/v1/test-cors-sb-route")
        def route_sb():
            raise SupabaseQueryError("Permission denied for table inventory_products", status_code=403)

        response = self.client.get("/api/v1/test-cors-sb-route", headers={"Origin": PROD_ORIGIN})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers.get("access-control-allow-origin"), PROD_ORIGIN)
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")
        self.assertIn("Permission denied", response.json().get("detail", ""))

    def test_cors_headers_on_500_unhandled_exception(self):
        """Verify unhandled exceptions return HTTP 500 JSON with full CORS headers."""
        @app.get("/api/v1/test-cors-500-route")
        def route_500():
            raise RuntimeError("Unexpected internal crash")

        response = self.client.get("/api/v1/test-cors-500-route", headers={"Origin": PROD_ORIGIN})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers.get("access-control-allow-origin"), PROD_ORIGIN)
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")
        self.assertIn("internal server error", response.json().get("detail", "").lower())

    def test_cors_headers_and_sanitization_on_supabase_500_error(self):
        """Verify 500 Supabase errors return safe generic detail and retain CORS headers."""
        from app.core.supabase import SupabaseError

        @app.get("/api/v1/test-cors-sb-500-route")
        def route_sb_500():
            raise SupabaseError("Secret internal database connection string")

        response = self.client.get("/api/v1/test-cors-sb-500-route", headers={"Origin": PROD_ORIGIN})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers.get("access-control-allow-origin"), PROD_ORIGIN)
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")
        self.assertEqual(response.json().get("detail"), "Database operation failed.")
        self.assertNotIn("Secret", response.text)


if __name__ == "__main__":
    unittest.main()
