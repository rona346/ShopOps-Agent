"""
API Integration tests for Action Execution and Reorder Tasks endpoints.
Tests /api/v1/approvals/{id}/execute and /api/v1/tasks.
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import AuthenticatedUser, get_current_user
from app.models.approval import ApprovalActionType, ApprovalRequestCreate
from app.models.inventory import ProductCreate
from app.services.approval import get_approval_service
from app.services.execution import get_action_execution_service, get_task_service
from app.services.inventory import get_inventory_service
from app.services.inventory_analysis import InventoryAnalysisService
from tests.fake_approval_repo import InMemoryApprovalRepository
from tests.fake_inventory_repo import InMemoryInventoryRepository
from tests.fake_task_repo import InMemoryTaskRepository


class TestExecutionAPI(unittest.TestCase):
    """Test suite for execution and task REST endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.inventory_repo = InMemoryInventoryRepository()
        cls.analysis_service = InventoryAnalysisService(inventory_service=cls.inventory_repo)
        cls.approval_repo = InMemoryApprovalRepository(
            inventory_service=cls.inventory_repo,
            analysis_service=cls.analysis_service,
        )
        cls.task_repo = InMemoryTaskRepository()

        app.dependency_overrides[get_inventory_service] = lambda: cls.inventory_repo
        app.dependency_overrides[get_approval_service] = lambda: cls.approval_repo
        app.dependency_overrides[get_task_service] = lambda: cls.task_repo
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
        self.task_repo.clear()

        # Seed low stock product
        self.prod = self.inventory_repo.create_product(
            ProductCreate(
                name="Sparkling Water",
                sku="WTR-SPK",
                category="Beverages",
                quantity=4,
                reorder_point=10,
                unit_cost=1.20,
            )
        )

    def _setup_approved_request(self) -> str:
        req = self.approval_repo.create_request(
            ApprovalRequestCreate(
                action_type=ApprovalActionType.REORDER,
                product_id=self.prod.id,
                sku=self.prod.sku,
                product_name=self.prod.name,
                current_quantity=4,
                proposed_reorder_quantity=16,
                reason="Stock low.",
                estimated_cost=19.20,
            )
        )
        self.approval_repo.approve_request(req.id, notes="Approved.")
        return req.id

    def test_execute_approval_endpoint_success(self):
        approval_id = self._setup_approved_request()

        res = self.client.post(f"/api/v1/approvals/{approval_id}/execute?execution_notes=PO-2026-001")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("id", data)
        self.assertEqual(data["approval_id"], approval_id)
        self.assertEqual(data["product_id"], self.prod.id)
        self.assertEqual(data["approved_reorder_quantity"], 16)
        self.assertEqual(data["status"], "created")
        self.assertEqual(data["notes"], "PO-2026-001")

        # Verify underlying approval status is now executed
        appr_res = self.client.get(f"/api/v1/approvals/{approval_id}")
        self.assertEqual(appr_res.json()["status"], "executed")

    def test_execute_pending_request_returns_400(self):
        req = self.approval_repo.create_request(
            ApprovalRequestCreate(
                action_type=ApprovalActionType.REORDER,
                product_id=self.prod.id,
                sku=self.prod.sku,
                product_name=self.prod.name,
                current_quantity=4,
                proposed_reorder_quantity=16,
                reason="Stock low.",
            )
        )
        res = self.client.post(f"/api/v1/approvals/{req.id}/execute")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Only requests with status 'approved' can be executed", res.json()["detail"])

    def test_execute_duplicate_returns_400(self):
        approval_id = self._setup_approved_request()
        # First execution succeeds
        res1 = self.client.post(f"/api/v1/approvals/{approval_id}/execute")
        self.assertEqual(res1.status_code, 201)

        # Duplicate execution returns 400
        res2 = self.client.post(f"/api/v1/approvals/{approval_id}/execute")
        self.assertEqual(res2.status_code, 400)

    def test_list_tasks_and_pagination(self):
        approval_id = self._setup_approved_request()
        self.client.post(f"/api/v1/approvals/{approval_id}/execute")

        res = self.client.get("/api/v1/tasks")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["items"][0]["approval_id"], approval_id)

    def test_get_task_by_id(self):
        approval_id = self._setup_approved_request()
        exec_res = self.client.post(f"/api/v1/approvals/{approval_id}/execute")
        task_id = exec_res.json()["id"]

        res = self.client.get(f"/api/v1/tasks/{task_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], task_id)

    def test_get_task_by_approval_id(self):
        approval_id = self._setup_approved_request()
        exec_res = self.client.post(f"/api/v1/approvals/{approval_id}/execute")
        task_id = exec_res.json()["id"]

        res = self.client.get(f"/api/v1/tasks/by-approval/{approval_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], task_id)

    def test_get_task_by_nonexistent_approval_id_returns_404(self):
        res = self.client.get("/api/v1/tasks/by-approval/missing_appr_id")
        self.assertEqual(res.status_code, 404)

    def test_firestore_task_service_unconfigured_returns_503(self):
        app.dependency_overrides.clear()
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            uid="test_owner", email="owner@shopops.local", role="owner"
        )
        try:
            live_client = TestClient(app)
            res = live_client.get("/api/v1/tasks")
            self.assertEqual(res.status_code, 503)
            self.assertIn("unavailable", res.json()["detail"].lower())
        finally:
            app.dependency_overrides[get_inventory_service] = lambda: self.inventory_repo
            app.dependency_overrides[get_approval_service] = lambda: self.approval_repo
            app.dependency_overrides[get_task_service] = lambda: self.task_repo
            app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
                uid="test_owner", email="owner@shopops.local", role="owner"
            )


if __name__ == "__main__":
    unittest.main()
