"""
API Integration tests for Owner Approval Workflow endpoints (/api/v1/approvals).
Uses FastAPI TestClient, isolated in-memory repositories, and unconfigured Firestore tests.
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import AuthenticatedUser, get_current_user
from app.models.approval import ApprovalStatus
from app.services.approval import get_approval_service
from app.services.inventory import get_inventory_service
from app.services.inventory_analysis import InventoryAnalysisService
from tests.fake_approval_repo import InMemoryApprovalRepository
from tests.fake_inventory_repo import InMemoryInventoryRepository


class TestApprovalAPI(unittest.TestCase):
    """Test suite for approval REST API endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.inventory_repo = InMemoryInventoryRepository()
        cls.analysis_service = InventoryAnalysisService(inventory_service=cls.inventory_repo)
        cls.approval_repo = InMemoryApprovalRepository(
            inventory_service=cls.inventory_repo,
            analysis_service=cls.analysis_service,
        )

        app.dependency_overrides[get_inventory_service] = lambda: cls.inventory_repo
        app.dependency_overrides[get_approval_service] = lambda: cls.approval_repo
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            uid="test_owner", email="owner@shopops.local", role="owner"
        )
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def setUp(self):
        self.inventory_repo.clear()
        self.approval_repo.clear()

        # Seed low stock item
        self.prod_low = self.inventory_repo.create_product(
            self.inventory_repo.create_product.__annotations__["product_in"](
                name="Olive Oil",
                sku="OIL-OLV",
                category="Pantry",
                quantity=1,
                reorder_point=10,
                unit_cost=20.0,
            )
        )
        # Seed healthy item
        self.prod_ok = self.inventory_repo.create_product(
            self.inventory_repo.create_product.__annotations__["product_in"](
                name="Salt",
                sku="SLT-01",
                category="Pantry",
                quantity=30,
                reorder_point=10,
                unit_cost=1.0,
            )
        )

    def test_create_approval_manual(self):
        payload = {
            "action_type": "reorder",
            "product_id": self.prod_low.id,
            "sku": "OIL-OLV",
            "product_name": "Olive Oil",
            "current_quantity": 1,
            "proposed_reorder_quantity": 19,
            "reason": "Replenish depleted pantry inventory.",
            "estimated_cost": 380.0,
        }
        res = self.client.post("/api/v1/approvals", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["proposed_reorder_quantity"], 19)

    def test_create_approval_from_recommendation_success(self):
        res = self.client.post(
            "/api/v1/approvals/from-recommendation",
            json={"product_id": self.prod_low.id},
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["product_id"], self.prod_low.id)
        self.assertEqual(data["proposed_reorder_quantity"], 19)  # 20 - 1
        self.assertEqual(data["estimated_cost"], 380.0)  # 19 * 20.0

    def test_create_from_recommendation_when_not_needed_returns_400(self):
        res = self.client.post(
            "/api/v1/approvals/from-recommendation",
            json={"product_id": self.prod_ok.id},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("recommended reorder quantity of 0", res.json()["detail"])

    def test_list_and_filter_approvals(self):
        # Create 2 approvals
        res1 = self.client.post(
            "/api/v1/approvals/from-recommendation", json={"product_id": self.prod_low.id}
        )
        id1 = res1.json()["id"]

        # Approve one of them
        self.client.post(f"/api/v1/approvals/{id1}/approve")

        # Query pending
        res_pending = self.client.get("/api/v1/approvals?status=pending")
        self.assertEqual(res_pending.status_code, 200)
        self.assertEqual(res_pending.json()["total"], 0)

        # Query approved
        res_approved = self.client.get("/api/v1/approvals?status=approved")
        self.assertEqual(res_approved.status_code, 200)
        self.assertEqual(res_approved.json()["total"], 1)

    def test_get_approval_by_id(self):
        create_res = self.client.post(
            "/api/v1/approvals/from-recommendation", json={"product_id": self.prod_low.id}
        )
        req_id = create_res.json()["id"]

        res = self.client.get(f"/api/v1/approvals/{req_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], req_id)

    def test_get_nonexistent_approval_returns_404(self):
        res = self.client.get("/api/v1/approvals/missing_id")
        self.assertEqual(res.status_code, 404)

    def test_edit_proposed_quantity_endpoint(self):
        create_res = self.client.post(
            "/api/v1/approvals/from-recommendation", json={"product_id": self.prod_low.id}
        )
        req_id = create_res.json()["id"]

        patch_res = self.client.patch(
            f"/api/v1/approvals/{req_id}",
            json={"proposed_reorder_quantity": 25, "notes": "Increasing batch size."},
        )
        self.assertEqual(patch_res.status_code, 200)
        data = patch_res.json()
        self.assertEqual(data["proposed_reorder_quantity"], 25)
        self.assertEqual(data["estimated_cost"], 500.0)  # 25 * 20.0
        self.assertEqual(data["owner_notes"], "Increasing batch size.")

    def test_edit_negative_quantity_returns_422(self):
        create_res = self.client.post(
            "/api/v1/approvals/from-recommendation", json={"product_id": self.prod_low.id}
        )
        req_id = create_res.json()["id"]

        patch_res = self.client.patch(
            f"/api/v1/approvals/{req_id}",
            json={"proposed_reorder_quantity": -10},
        )
        self.assertEqual(patch_res.status_code, 422)

    def test_approve_lifecycle_endpoint(self):
        create_res = self.client.post(
            "/api/v1/approvals/from-recommendation", json={"product_id": self.prod_low.id}
        )
        req_id = create_res.json()["id"]

        approve_res = self.client.post(
            f"/api/v1/approvals/{req_id}/approve",
            json={"notes": "Approved by owner."},
        )
        self.assertEqual(approve_res.status_code, 200)
        data = approve_res.json()
        self.assertEqual(data["status"], "approved")
        self.assertEqual(data["owner_notes"], "Approved by owner.")
        self.assertIsNotNone(data["decided_at"])

        # Second approve fails with 400
        dup_res = self.client.post(f"/api/v1/approvals/{req_id}/approve")
        self.assertEqual(dup_res.status_code, 400)
        self.assertIn("already been approved", dup_res.json()["detail"])

    def test_reject_lifecycle_endpoint(self):
        create_res = self.client.post(
            "/api/v1/approvals/from-recommendation", json={"product_id": self.prod_low.id}
        )
        req_id = create_res.json()["id"]

        reject_res = self.client.post(
            f"/api/v1/approvals/{req_id}/reject",
            json={"notes": "Holding off due to supplier delay."},
        )
        self.assertEqual(reject_res.status_code, 200)
        data = reject_res.json()
        self.assertEqual(data["status"], "rejected")

        # Second reject fails with 400
        dup_res = self.client.post(f"/api/v1/approvals/{req_id}/reject")
        self.assertEqual(dup_res.status_code, 400)
        self.assertIn("already been rejected", dup_res.json()["detail"])

    def test_firestore_approval_unconfigured_returns_503(self):
        # Clear service overrides but keep auth so request reaches Firestore
        app.dependency_overrides.clear()
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            uid="test_owner", email="owner@shopops.local", role="owner"
        )
        try:
            live_client = TestClient(app)
            res = live_client.get("/api/v1/approvals")
            self.assertEqual(res.status_code, 503)
            self.assertIn("unavailable", res.json()["detail"].lower())
        finally:
            # Re-apply overrides for tearDown
            app.dependency_overrides[get_inventory_service] = lambda: self.inventory_repo
            app.dependency_overrides[get_approval_service] = lambda: self.approval_repo
            app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
                uid="test_owner", email="owner@shopops.local", role="owner"
            )


if __name__ == "__main__":
    unittest.main()
