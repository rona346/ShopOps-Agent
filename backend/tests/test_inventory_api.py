"""
Unit and API integration tests for Inventory REST endpoints.
Uses isolated in-memory repository via FastAPI dependency override.
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import AuthenticatedUser, get_current_user
from app.services.inventory import get_inventory_service
from tests.fake_inventory_repo import InMemoryInventoryRepository


class TestInventoryAPI(unittest.TestCase):
    """Test suite for CRUD, search, pagination, and low-stock endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.fake_repo = InMemoryInventoryRepository()
        # Override get_inventory_service with test repository
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

    def test_create_product_success(self):
        payload = {
            "name": "Organic Honey",
            "sku": "honey-500g",
            "category": "Groceries",
            "quantity": 20,
            "reorder_point": 5,
            "unit": "jar",
            "unit_cost": 8.50,
            "supplier_name": "Bee Farm",
            "description": "Raw unpasteurized honey",
        }
        res = self.client.post("/api/v1/inventory", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("id", data)
        self.assertEqual(data["name"], "Organic Honey")
        self.assertEqual(data["sku"], "HONEY-500G")
        self.assertEqual(data["quantity"], 20)
        self.assertFalse(data["is_low_stock"])

    def test_create_duplicate_sku_fails(self):
        payload = {
            "name": "Coffee Beans",
            "sku": "COFFEE-01",
            "category": "Beverages",
            "quantity": 10,
        }
        res1 = self.client.post("/api/v1/inventory", json=payload)
        self.assertEqual(res1.status_code, 201)

        # Second creation with identical SKU
        res2 = self.client.post("/api/v1/inventory", json=payload)
        self.assertEqual(res2.status_code, 400)
        self.assertIn("already exists", res2.json()["detail"])

    def test_get_product_by_id(self):
        payload = {"name": "Green Tea", "sku": "TEA-GRN", "category": "Beverages", "quantity": 12}
        create_res = self.client.post("/api/v1/inventory", json=payload)
        prod_id = create_res.json()["id"]

        res = self.client.get(f"/api/v1/inventory/{prod_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["name"], "Green Tea")
        self.assertEqual(res.json()["id"], prod_id)

    def test_get_nonexistent_product_returns_404(self):
        res = self.client.get("/api/v1/inventory/non_existent_id")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    def test_list_and_pagination(self):
        # Create 5 products
        for i in range(5):
            self.client.post(
                "/api/v1/inventory",
                json={
                    "name": f"Item {i}",
                    "sku": f"SKU-{i}",
                    "category": "Test",
                    "quantity": i * 5,
                },
            )

        # Fetch page with limit 2, offset 0
        res = self.client.get("/api/v1/inventory?limit=2&offset=0")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["total"], 5)
        self.assertEqual(len(body["items"]), 2)
        self.assertEqual(body["limit"], 2)
        self.assertEqual(body["offset"], 0)

        # Fetch next page
        res2 = self.client.get("/api/v1/inventory?limit=2&offset=2")
        self.assertEqual(len(res2.json()["items"]), 2)

    def test_search_by_name_and_sku(self):
        self.client.post(
            "/api/v1/inventory",
            json={"name": "Almond Milk", "sku": "MILK-ALM", "category": "Dairy", "quantity": 10},
        )
        self.client.post(
            "/api/v1/inventory",
            json={"name": "Oat Milk", "sku": "MILK-OAT", "category": "Dairy", "quantity": 15},
        )
        self.client.post(
            "/api/v1/inventory",
            json={"name": "Apple Cider", "sku": "JCE-APL", "category": "Beverages", "quantity": 8},
        )

        # Search by name substring
        res = self.client.get("/api/v1/inventory?search=almond")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["total"], 1)
        self.assertEqual(res.json()["items"][0]["name"], "Almond Milk")

        # Search by SKU
        res_sku = self.client.get("/api/v1/inventory?search=JCE-APL")
        self.assertEqual(res_sku.status_code, 200)
        self.assertEqual(res_sku.json()["total"], 1)
        self.assertEqual(res_sku.json()["items"][0]["sku"], "JCE-APL")

    def test_low_stock_filter_and_endpoint(self):
        # Low stock item (quantity 3 <= reorder_point 10)
        self.client.post(
            "/api/v1/inventory",
            json={"name": "Sugar", "sku": "SGR-01", "category": "Baking", "quantity": 3, "reorder_point": 10},
        )
        # Healthy item (quantity 50 > reorder_point 10)
        self.client.post(
            "/api/v1/inventory",
            json={"name": "Flour", "sku": "FLR-01", "category": "Baking", "quantity": 50, "reorder_point": 10},
        )

        # Filter via query param
        res_filter = self.client.get("/api/v1/inventory?low_stock=true")
        self.assertEqual(res_filter.status_code, 200)
        self.assertEqual(res_filter.json()["total"], 1)
        self.assertEqual(res_filter.json()["items"][0]["sku"], "SGR-01")

        # Query dedicated low-stock endpoint
        res_endpoint = self.client.get("/api/v1/inventory/low-stock")
        self.assertEqual(res_endpoint.status_code, 200)
        self.assertEqual(res_endpoint.json()["total"], 1)
        self.assertEqual(res_endpoint.json()["items"][0]["sku"], "SGR-01")

    def test_patch_update_product(self):
        create_res = self.client.post(
            "/api/v1/inventory",
            json={"name": "Olive Oil", "sku": "OIL-OLV", "category": "Pantry", "quantity": 10},
        )
        prod_id = create_res.json()["id"]

        # Update only quantity and unit_cost
        patch_res = self.client.patch(
            f"/api/v1/inventory/{prod_id}",
            json={"quantity": 25, "unit_cost": 14.99},
        )
        self.assertEqual(patch_res.status_code, 200)
        updated = patch_res.json()
        self.assertEqual(updated["quantity"], 25)
        self.assertEqual(updated["unit_cost"], 14.99)
        self.assertEqual(updated["name"], "Olive Oil")  # Unmodified

    def test_patch_duplicate_sku_fails(self):
        self.client.post(
            "/api/v1/inventory",
            json={"name": "Item A", "sku": "SKU-A", "category": "General", "quantity": 5},
        )
        res_b = self.client.post(
            "/api/v1/inventory",
            json={"name": "Item B", "sku": "SKU-B", "category": "General", "quantity": 5},
        )
        id_b = res_b.json()["id"]

        # Attempt to rename Item B's SKU to SKU-A
        patch_res = self.client.patch(f"/api/v1/inventory/{id_b}", json={"sku": "SKU-A"})
        self.assertEqual(patch_res.status_code, 400)
        self.assertIn("already exists", patch_res.json()["detail"])

    def test_delete_product(self):
        create_res = self.client.post(
            "/api/v1/inventory",
            json={"name": "Paper Towels", "sku": "TOWEL-01", "category": "Supplies", "quantity": 20},
        )
        prod_id = create_res.json()["id"]

        del_res = self.client.delete(f"/api/v1/inventory/{prod_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()["id"], prod_id)

        # Confirm 404 on subsequent get
        get_res = self.client.get(f"/api/v1/inventory/{prod_id}")
        self.assertEqual(get_res.status_code, 404)

    def test_delete_nonexistent_product_returns_404(self):
        res = self.client.delete("/api/v1/inventory/non_existent_id")
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
