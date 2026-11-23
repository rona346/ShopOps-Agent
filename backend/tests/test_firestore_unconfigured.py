"""
Tests for Firestore Service behavior when Firebase credentials are not configured.
Verifies clean 503 Service Unavailable responses and FirebaseUnavailableError handling.
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import AuthenticatedUser, get_current_user
from app.services.inventory import (
    FirebaseUnavailableError,
    FirestoreInventoryService,
)
from app.models.inventory import ProductCreate


class TestFirestoreUnconfigured(unittest.TestCase):
    """
    Tests real FirestoreInventoryService behavior when credentials are missing.
    Ensures that no mock fallback silently executes in production code.
    """

    def setUp(self):
        # Ensure no service dependency overrides are active, but authenticate request
        app.dependency_overrides.clear()
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            uid="test_owner", email="owner@shopops.local", role="owner"
        )
        self.client = TestClient(app)

    def test_firestore_service_raises_when_unconfigured(self):
        service = FirestoreInventoryService()
        with self.assertRaises(FirebaseUnavailableError):
            service.create_product(
                ProductCreate(
                    name="Test Item",
                    sku="TEST-SKU",
                    category="Test",
                    quantity=10,
                )
            )

    def test_inventory_api_returns_503_when_unconfigured(self):
        # Calls the live endpoint without dependency overrides
        res = self.client.get("/api/v1/inventory")
        self.assertEqual(res.status_code, 503)
        body = res.json()
        self.assertIn("detail", body)
        self.assertIn("unavailable", body["detail"].lower())

    def test_health_endpoint_still_healthy_without_firebase(self):
        # Core health endpoint remains functional independent of Firebase
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")


if __name__ == "__main__":
    unittest.main()
