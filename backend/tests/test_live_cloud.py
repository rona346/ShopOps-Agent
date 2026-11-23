"""
Live Cloud Integration Verification for Firebase Firestore and Google Gemini API.
Strict Rules:
- Only runs live network calls if valid credentials are set in backend/.env.
- Never uses fake in-memory repositories for live tests.
- If credentials are missing, reports BLOCKED with clear configuration instructions.
- Never prints or exposes secrets.
"""

import sys
import unittest
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core import firebase, gemini
from app.core.config import settings
from app.models.inventory import ProductCreate
from app.services.inventory import FirestoreInventoryService
from app.services.approval import FirestoreApprovalService
from app.services.execution import FirestoreTaskService, ActionExecutionService
from app.services.inventory_analysis import InventoryAnalysisService
from app.services.agent import InventoryAgentService


class TestLiveCloudIntegration(unittest.TestCase):
    """Live cloud integration test runner."""

    def test_live_firestore_integration(self):
        """Verifies real Firestore document persistence and task creation if credentials exist."""
        if not firebase.is_firebase_configured():
            print("\n  [BLOCKED] Live Firebase Firestore integration test: BLOCKED")
            print("    Reason: FIREBASE_CREDENTIALS_PATH or FIREBASE_PROJECT_ID is not configured in backend/.env.")
            self.skipTest("Firebase credentials not configured in backend/.env")

        print("\n  [RUNNING] Live Firestore credentials detected. Executing cloud verification...")
        inv_service = FirestoreInventoryService()
        analysis_service = InventoryAnalysisService(inventory_service=inv_service)
        approval_service = FirestoreApprovalService(
            inventory_service=inv_service, analysis_service=analysis_service
        )
        task_service = FirestoreTaskService()
        execution_service = ActionExecutionService(
            approval_service=approval_service,
            task_service=task_service,
            inventory_service=inv_service,
        )

        test_sku = f"LIVE-{uuid.uuid4().hex[:6].upper()}"
        created_prod = None
        try:
            # 1. Create live product
            prod_in = ProductCreate(
                name="Live Cloud Integration Test Item",
                sku=test_sku,
                category="Testing",
                quantity=3,
                reorder_point=10,
                unit_cost=5.0,
            )
            created_prod = inv_service.create_product(prod_in)
            self.assertIsNotNone(created_prod.id)
            print(f"    - Live Product persisted to Firestore (ID: {created_prod.id})")

            # 2. Create live approval from recommendation
            appr = approval_service.create_from_recommendation(created_prod.id)
            self.assertEqual(appr.status.value, "pending")
            print(f"    - Live Approval persisted to Firestore (ID: {appr.id})")

            # 3. Approve
            approved = approval_service.approve_request(appr.id, notes="Live test approved")
            self.assertEqual(approved.status.value, "approved")

            # 4. Execute
            task = execution_service.execute_approval(appr.id, execution_notes="Live task execution")
            self.assertEqual(task.status.value, "created")
            print(f"    - Live Reorder Task persisted to Firestore (ID: {task.id})")

            # 5. Verify task persisted
            retrieved_task = task_service.get_task(task.id)
            self.assertEqual(retrieved_task.id, task.id)

            # 6. Verify approval status is executed
            appr_updated = approval_service.get_request(appr.id)
            self.assertEqual(appr_updated.status.value, "executed")

            # 7. Verify inventory quantity unchanged
            prod_check = inv_service.get_product(created_prod.id)
            self.assertEqual(prod_check.quantity, 3)

            # 8. Verify duplicate execution idempotency on real Firestore
            with self.assertRaises(Exception):
                execution_service.execute_approval(appr.id)
            print("    - Live Firestore verified idempotency: Duplicate execution blocked.")

            print("  [PASS] Live Firebase Firestore integration verified successfully!")
        finally:
            # Cleanup live documents
            if created_prod:
                try:
                    inv_service.delete_product(created_prod.id)
                    print(f"    - Cleaned up live test product (ID: {created_prod.id})")
                except Exception:
                    pass

    def test_live_gemini_integration(self):
        """Verifies real Gemini API communication and schema adherence if key is set."""
        if not gemini.is_gemini_configured():
            print("\n  [BLOCKED] Live Gemini API integration test: BLOCKED")
            print("    Reason: GEMINI_API_KEY is not configured in backend/.env.")
            self.skipTest("GEMINI_API_KEY not configured in backend/.env")

        print("\n  [RUNNING] Live Gemini API key detected. Querying Gemini model...")
        inv_service = FirestoreInventoryService()
        analysis_service = InventoryAnalysisService(inventory_service=inv_service)
        agent_service = InventoryAgentService(analysis_service=analysis_service)

        # 1. Executive Insights
        insights = agent_service.generate_inventory_insights()
        self.assertIsNotNone(insights.summary)
        self.assertTrue(len(insights.summary) > 10)
        print("    - Gemini generate_inventory_insights() response received and validated.")

        # 2. Query Agent
        query_res = agent_service.answer_inventory_query("What is our general stock health?")
        self.assertIsNotNone(query_res.answer)
        self.assertTrue(len(query_res.answer) > 5)
        print("    - Gemini answer_inventory_query() response received and validated.")

        print("  [PASS] Live Gemini API integration verified successfully!")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLiveCloudIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
