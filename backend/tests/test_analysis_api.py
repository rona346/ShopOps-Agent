"""
API tests for Inventory Analysis and Reorder Planning Endpoints.
Uses TestClient with isolated in-memory repository.
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import AuthenticatedUser, get_current_user
from app.services.inventory import get_inventory_service
from tests.fake_inventory_repo import InMemoryInventoryRepository


class TestInventoryAnalysisAPI(unittest.TestCase):
    """Test suite for /api/v1/inventory/analysis and /reorder-recommendations."""

    @classmethod
    def setUpClass(cls):
        cls.fake_repo = InMemoryInventoryRepository()
        app.dependency_overrides[get_inventory_service] = lambda: cls.fake_repo
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            uid="test_owner", email="owner@shopops.local", role="owner"
        )
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def setUp(self):
        self.fake_repo.clear()

    def test_analysis_endpoint_returns_metrics(self):
        # Create an out-of-stock item
        self.client.post(
            "/api/v1/inventory",
            json={
                "name": "Coffee",
                "sku": "COF-01",
                "category": "Beverages",
                "quantity": 0,
                "reorder_point": 10,
                "unit_cost": 15.0,
            },
        )
        # Create an overstocked item
        self.client.post(
            "/api/v1/inventory",
            json={
                "name": "Napkins",
                "sku": "NAP-01",
                "category": "Supplies",
                "quantity": 100,
                "reorder_point": 10,
                "unit_cost": 1.0,
            },
        )

        res = self.client.get("/api/v1/inventory/analysis")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["total_products"], 2)
        self.assertEqual(data["out_of_stock_count"], 1)
        self.assertEqual(data["overstock_count"], 1)
        self.assertEqual(data["total_recommended_reorder_units"], 20)  # max(10*2, 10) = 20
        self.assertEqual(data["estimated_total_reorder_cost"], 300.0)  # 20 * 15.0

        # Verify items list has detailed reasons and status
        items = data["items"]
        self.assertEqual(len(items), 2)
        item_map = {item["sku"]: item for item in items}
        self.assertEqual(item_map["COF-01"]["status"], "out_of_stock")
        self.assertEqual(item_map["NAP-01"]["status"], "overstock")

    def test_reorder_recommendations_endpoint(self):
        # Create 1 low stock item and 1 normal item
        self.client.post(
            "/api/v1/inventory",
            json={
                "name": "Sugar",
                "sku": "SGR-01",
                "category": "Baking",
                "quantity": 3,
                "reorder_point": 10,
                "unit_cost": 4.0,
            },
        )
        self.client.post(
            "/api/v1/inventory",
            json={
                "name": "Flour",
                "sku": "FLR-01",
                "category": "Baking",
                "quantity": 20,
                "reorder_point": 10,
                "unit_cost": 3.0,
            },
        )

        res = self.client.get("/api/v1/inventory/reorder-recommendations")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["total_items_to_reorder"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["sku"], "SGR-01")
        self.assertEqual(data["total_recommended_units"], 17)  # 20 - 3
        self.assertEqual(data["estimated_total_cost"], 68.0)  # 17 * 4.0

    def test_category_filter_on_analysis(self):
        self.client.post(
            "/api/v1/inventory",
            json={"name": "Tea", "sku": "TEA-01", "category": "Beverages", "quantity": 1},
        )
        self.client.post(
            "/api/v1/inventory",
            json={"name": "Spoon", "sku": "SPN-01", "category": "Utensils", "quantity": 1},
        )

        res = self.client.get("/api/v1/inventory/analysis?category=Beverages")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_products"], 1)
        self.assertEqual(data["items"][0]["category"], "Beverages")

    def test_empty_inventory_analysis(self):
        res = self.client.get("/api/v1/inventory/analysis")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_products"], 0)
        self.assertEqual(data["total_inventory_units"], 0)
        self.assertEqual(data["out_of_stock_count"], 0)
        self.assertEqual(data["items"], [])


if __name__ == "__main__":
    unittest.main()
