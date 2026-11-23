"""
ShopOps Agent - Phase 8 Local End-to-End Smoke Test.
Verifies the complete MVP operational workflow:
1. Backend health check and frontend loading.
2. Create a test inventory product.
3. Confirm the product appears in the inventory dashboard.
4. Set quantity below its reorder point and verify deterministic analysis.
5. Create an approval from the reorder recommendation.
6. Approve the request.
7. Execute the approved request using execution endpoint.
8. Verify the internal reorder task appears in the task list.
9. Verify the approval status becomes 'executed'.
10. Verify inventory quantity remains unchanged (non-destructive execution).
11. Verify duplicate execution is blocked.
12. Verify frontend/backend displays configuration errors for unconfigured Firebase & Gemini.
"""

import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.auth import AuthenticatedUser, get_current_user
from app.services.inventory import get_inventory_service
from app.services.approval import get_approval_service
from app.services.execution import get_task_service
from app.services.inventory_analysis import InventoryAnalysisService

from tests.fake_inventory_repo import InMemoryInventoryRepository
from tests.fake_approval_repo import InMemoryApprovalRepository
from tests.fake_task_repo import InMemoryTaskRepository


class ShopOpsEndToEndSmokeTest(unittest.TestCase):
    """Smoke test covering all 12 operational verification steps."""

    @classmethod
    def setUpClass(cls):
        # Repositories for testing MVP workflow
        cls.inventory_repo = InMemoryInventoryRepository()
        cls.analysis_service = InventoryAnalysisService(inventory_service=cls.inventory_repo)
        cls.approval_repo = InMemoryApprovalRepository(
            inventory_service=cls.inventory_repo,
            analysis_service=cls.analysis_service,
        )
        cls.task_repo = InMemoryTaskRepository()

        # Set up dependency overrides
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

    def test_step_01_backend_health_check(self):
        """Step 1: Backend health check returns healthy status."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "ShopOps Agent API")
        print("  [STEP 1 PASS] Backend /health reports healthy status.")

    def test_step_02_to_11_complete_operational_workflow(self):
        """Steps 2 through 11: Full product -> analysis -> approval -> execution -> invariant cycle."""
        test_sku = "SMOKE-MILK-001"
        test_product_name = "Smoke Test Almond Milk 1L"

        # --- STEP 2: Create a test inventory product ---
        create_payload = {
            "name": test_product_name,
            "sku": test_sku,
            "category": "Dairy Alternatives",
            "quantity": 50,
            "reorder_point": 20,
            "unit": "carton",
            "unit_cost": 3.75,
            "supplier_name": "Smoke Test Vendor Ltd",
            "description": "Product used exclusively for Phase 8 smoke testing.",
        }
        res_create = self.client.post("/api/v1/inventory", json=create_payload)
        self.assertEqual(res_create.status_code, 201, f"Product creation failed: {res_create.text}")
        prod_data = res_create.json()
        product_id = prod_data["id"]
        self.assertEqual(prod_data["sku"], test_sku)
        self.assertEqual(prod_data["quantity"], 50)
        self.assertFalse(prod_data["is_low_stock"])
        print(f"  [STEP 2 PASS] Created test product ID: {product_id} (SKU: {test_sku}, Qty: 50).")

        # --- STEP 3: Confirm product appears in inventory list ---
        res_list = self.client.get(f"/api/v1/inventory?search={test_sku}")
        self.assertEqual(res_list.status_code, 200)
        list_data = res_list.json()
        self.assertGreaterEqual(list_data["total"], 1)
        found_item = next((item for item in list_data["items"] if item["id"] == product_id), None)
        self.assertIsNotNone(found_item, "Created product not found in inventory list query.")
        self.assertEqual(found_item["name"], test_product_name)
        print("  [STEP 3 PASS] Product confirmed present in inventory catalog query.")

        # --- STEP 4: Set quantity below reorder point & verify deterministic analysis ---
        patch_payload = {"quantity": 8}  # Reorder point is 20, so 8 is low stock
        res_patch = self.client.patch(f"/api/v1/inventory/{product_id}", json=patch_payload)
        self.assertEqual(res_patch.status_code, 200)
        patched_data = res_patch.json()
        self.assertEqual(patched_data["quantity"], 8)
        self.assertTrue(patched_data["is_low_stock"])

        # Check deterministic analysis
        res_analysis = self.client.get("/api/v1/inventory/analysis")
        self.assertEqual(res_analysis.status_code, 200)
        analysis_data = res_analysis.json()
        analysis_item = next((i for i in analysis_data["items"] if i["product_id"] == product_id), None)
        self.assertIsNotNone(analysis_item, "Product missing from analysis items.")
        self.assertEqual(analysis_item["status"], "low_stock")
        # Formula: (reorder_point * 2) - quantity = (20 * 2) - 8 = 32
        expected_reorder_qty = 32
        expected_reorder_cost = round(expected_reorder_qty * 3.75, 2)
        self.assertEqual(analysis_item["recommended_reorder_quantity"], expected_reorder_qty)
        self.assertEqual(analysis_item["estimated_reorder_cost"], expected_reorder_cost)
        print(f"  [STEP 4 PASS] Patched qty to 8 (<20). Deterministic analysis: status='low_stock', recommended={expected_reorder_qty}, cost=${expected_reorder_cost}.")

        # --- STEP 5: Create approval from reorder recommendation ---
        res_appr_create = self.client.post(
            "/api/v1/approvals/from-recommendation",
            json={"product_id": product_id},
        )
        self.assertEqual(res_appr_create.status_code, 201)
        appr_data = res_appr_create.json()
        approval_id = appr_data["id"]
        self.assertEqual(appr_data["status"], "pending")
        self.assertEqual(appr_data["proposed_reorder_quantity"], expected_reorder_qty)
        self.assertEqual(appr_data["estimated_cost"], expected_reorder_cost)

        # Also test owner editing proposed quantity while pending
        new_proposed_qty = 30
        res_edit_qty = self.client.patch(
            f"/api/v1/approvals/{approval_id}",
            json={"proposed_reorder_quantity": new_proposed_qty, "notes": "Adjusted to case of 30 units."},
        )
        self.assertEqual(res_edit_qty.status_code, 200)
        edited_appr = res_edit_qty.json()
        self.assertEqual(edited_appr["proposed_reorder_quantity"], 30)
        self.assertEqual(edited_appr["estimated_cost"], round(30 * 3.75, 2))
        print(f"  [STEP 5 PASS] Approval request {approval_id} created as 'pending'. Quantity edited to 30 units.")

        # --- STEP 6: Approve the request ---
        res_approve = self.client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            json={"notes": "Approved by store owner for morning restocking."},
        )
        self.assertEqual(res_approve.status_code, 200)
        approved_data = res_approve.json()
        self.assertEqual(approved_data["status"], "approved")
        self.assertIsNotNone(approved_data["decided_at"])
        print(f"  [STEP 6 PASS] Request {approval_id} successfully transitioned to 'approved'.")

        # --- STEP 7: Execute approved request (simulating frontend confirmation dialog) ---
        exec_notes = "Store manager generated internal reorder ticket."
        res_exec = self.client.post(
            f"/api/v1/approvals/{approval_id}/execute?execution_notes={exec_notes}"
        )
        self.assertEqual(res_exec.status_code, 201, f"Execution failed: {res_exec.text}")
        task_data = res_exec.json()
        self.assertIn("id", task_data)
        task_id = task_data["id"]
        self.assertEqual(task_data["approval_id"], approval_id)
        self.assertEqual(task_data["approved_reorder_quantity"], 30)
        self.assertEqual(task_data["status"], "created")
        self.assertEqual(task_data["notes"], exec_notes)
        print(f"  [STEP 7 PASS] Executed approval. Created internal reorder task ID: {task_id}.")

        # --- STEP 8: Verify internal reorder task appears in task list ---
        res_task_list = self.client.get("/api/v1/tasks")
        self.assertEqual(res_task_list.status_code, 200)
        tasks_data = res_task_list.json()
        found_task = next((t for t in tasks_data["items"] if t["id"] == task_id), None)
        self.assertIsNotNone(found_task, "Created task not found in /api/v1/tasks list.")
        self.assertEqual(found_task["sku"], test_sku)
        self.assertEqual(found_task["approved_reorder_quantity"], 30)
        self.assertEqual(found_task["status"], "created")

        # Also verify lookup by approval ID
        res_task_by_appr = self.client.get(f"/api/v1/tasks/by-approval/{approval_id}")
        self.assertEqual(res_task_by_appr.status_code, 200)
        self.assertEqual(res_task_by_appr.json()["id"], task_id)
        print(f"  [STEP 8 PASS] Reorder task {task_id} confirmed in task backlog with status 'created'.")

        # --- STEP 9: Verify approval status transitioned to 'executed' ---
        res_appr_check = self.client.get(f"/api/v1/approvals/{approval_id}")
        self.assertEqual(res_appr_check.status_code, 200)
        final_appr = res_appr_check.json()
        self.assertEqual(final_appr["status"], "executed")
        print(f"  [STEP 9 PASS] Approval {approval_id} confirmed in status 'executed'.")

        # --- STEP 10: Invariant check - inventory quantity remains unchanged ---
        res_inv_check = self.client.get(f"/api/v1/inventory/{product_id}")
        self.assertEqual(res_inv_check.status_code, 200)
        inv_check_data = res_inv_check.json()
        self.assertEqual(
            inv_check_data["quantity"],
            8,
            "CRITICAL INVARIANT VIOLATION: Inventory quantity was modified by execution!",
        )
        print(f"  [STEP 10 PASS] Invariant verified: Inventory quantity remains at 8 (non-destructive execution preserved).")

        # --- STEP 11: Idempotency check - duplicate execution blocked ---
        res_duplicate = self.client.post(
            f"/api/v1/approvals/{approval_id}/execute",
            json={"notes": "Duplicate execution attempt"},
        )
        self.assertEqual(
            res_duplicate.status_code,
            400,
            f"Expected HTTP 400 for duplicate execution, got: {res_duplicate.status_code}",
        )
        err_msg = res_duplicate.json().get("detail", "")
        self.assertTrue(
            "already been executed" in err_msg or "Cannot execute" in err_msg,
            f"Unexpected error detail on duplicate execution: {err_msg}",
        )
        print(f"  [STEP 11 PASS] Idempotency verified: Duplicate execution was blocked with HTTP 400 ({err_msg}).")

        # Clean up test product
        res_del = self.client.delete(f"/api/v1/inventory/{product_id}")
        self.assertEqual(res_del.status_code, 200)
        print("  [CLEANUP] Deleted test product after test.")

    def test_step_12_unconfigured_error_handling(self):
        """Step 12: Verify unconfigured Firebase and Gemini produce clean HTTP 503 responses."""
        # Test client with real un-overridden providers
        real_client = TestClient(app)

        # Clear any overrides temporarily to test unconfigured handling
        saved_overrides = dict(app.dependency_overrides)
        try:
            app.dependency_overrides.clear()

            # 1. Health endpoint still reports healthy even when Firebase is not configured
            res_health = real_client.get("/health")
            self.assertEqual(res_health.status_code, 200)
            self.assertEqual(res_health.json()["status"], "healthy")

            # 2. Unauthenticated request to protected endpoint is rejected with 401
            res_unauth = real_client.get("/api/v1/inventory")
            self.assertEqual(res_unauth.status_code, 401)

            # 3. Authenticated request reports 503 with informative Firebase message when unconfigured
            auth_headers = {"Authorization": f"Bearer {settings.DEV_AUTH_TOKEN}"}
            res_inv = real_client.get("/api/v1/inventory", headers=auth_headers)
            self.assertEqual(res_inv.status_code, 503)
            inv_err = res_inv.json().get("detail", "")
            self.assertIn("Firestore service is currently unavailable", inv_err)
            self.assertIn("Firebase credentials are not configured", inv_err)

            # 4. Agent insights endpoint reports 503 with informative Gemini message
            res_agent = real_client.get("/api/v1/agent/insights", headers=auth_headers)
            self.assertEqual(res_agent.status_code, 503)
            agent_err = res_agent.json().get("detail", "")
            self.assertIn("Gemini AI service is not configured", agent_err)
            self.assertIn("GEMINI_API_KEY", agent_err)

            # 5. Approvals endpoint reports 503 when Firebase is unavailable
            res_appr = real_client.get("/api/v1/approvals", headers=auth_headers)
            self.assertEqual(res_appr.status_code, 503)

            # 6. Tasks endpoint reports 503 when Firebase is unavailable
            res_tasks = real_client.get("/api/v1/tasks", headers=auth_headers)
            self.assertEqual(res_tasks.status_code, 503)

            print("  [STEP 12 PASS] Authentication verified (401 on unauthenticated) & unconfigured Firebase/Gemini services cleanly return HTTP 503.")
        finally:
            app.dependency_overrides.update(saved_overrides)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(ShopOpsEndToEndSmokeTest)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
