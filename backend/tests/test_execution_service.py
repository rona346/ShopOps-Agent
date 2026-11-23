"""
Unit tests for ActionExecutionService.
Tests approved request execution, rejection of illegal states, idempotency,
persistence verification, failure handling, and inventory immutability.
"""

import unittest
from app.models.approval import (
    ApprovalActionType,
    ApprovalRequestCreate,
    ApprovalStatus,
)
from app.models.inventory import ProductCreate
from app.models.task import TaskStatus
from app.services.execution import (
    ActionExecutionService,
    DuplicateExecutionError,
    InvalidExecutionStateError,
    TaskPersistenceError,
)
from app.services.inventory_analysis import InventoryAnalysisService
from tests.fake_approval_repo import InMemoryApprovalRepository
from tests.fake_inventory_repo import InMemoryInventoryRepository
from tests.fake_task_repo import InMemoryTaskRepository


class TestActionExecutionService(unittest.TestCase):
    """Test suite for operational action execution."""

    def setUp(self):
        self.inventory_repo = InMemoryInventoryRepository()
        self.analysis_service = InventoryAnalysisService(inventory_service=self.inventory_repo)
        self.approval_repo = InMemoryApprovalRepository(
            inventory_service=self.inventory_repo,
            analysis_service=self.analysis_service,
        )
        self.task_repo = InMemoryTaskRepository()

        self.execution_service = ActionExecutionService(
            approval_service=self.approval_repo,
            task_service=self.task_repo,
            inventory_service=self.inventory_repo,
        )

        # Seed low stock product
        self.prod = self.inventory_repo.create_product(
            ProductCreate(
                name="Coffee Beans",
                sku="COF-01",
                category="Beverages",
                quantity=3,
                reorder_point=10,
                unit_cost=15.0,
            )
        )

    def _create_approved_request(self) -> str:
        req = self.approval_repo.create_request(
            ApprovalRequestCreate(
                action_type=ApprovalActionType.REORDER,
                product_id=self.prod.id,
                sku=self.prod.sku,
                product_name=self.prod.name,
                current_quantity=3,
                proposed_reorder_quantity=17,
                reason="Stock low.",
                estimated_cost=255.0,
            )
        )
        self.approval_repo.approve_request(req.id, notes="Approved by owner.")
        return req.id

    def test_execute_approved_request_success(self):
        approval_id = self._create_approved_request()

        task = self.execution_service.execute_approval(
            approval_id=approval_id, execution_notes="Batch #101"
        )
        self.assertTrue(task.id.startswith("task_"))
        self.assertEqual(task.approval_id, approval_id)
        self.assertEqual(task.product_id, self.prod.id)
        self.assertEqual(task.sku, "COF-01")
        self.assertEqual(task.approved_reorder_quantity, 17)
        self.assertEqual(task.estimated_cost, 255.0)
        self.assertEqual(task.status, TaskStatus.CREATED)
        self.assertEqual(task.notes, "Batch #101")

        # Verify approval is now marked as EXECUTED
        approval = self.approval_repo.get_request(approval_id)
        self.assertEqual(approval.status, ApprovalStatus.EXECUTED)

        # Verify task is persisted in task repository
        persisted = self.task_repo.get_task(task.id)
        self.assertEqual(persisted.id, task.id)

        # CRITICAL: Verify inventory stock quantity is NOT modified in this phase
        prod_check = self.inventory_repo.get_product(self.prod.id)
        self.assertEqual(prod_check.quantity, 3)

    def test_cannot_execute_pending_request(self):
        req = self.approval_repo.create_request(
            ApprovalRequestCreate(
                action_type=ApprovalActionType.REORDER,
                product_id=self.prod.id,
                sku=self.prod.sku,
                product_name=self.prod.name,
                current_quantity=3,
                proposed_reorder_quantity=17,
                reason="Stock low.",
            )
        )
        with self.assertRaises(InvalidExecutionStateError) as ctx:
            self.execution_service.execute_approval(req.id)
        self.assertIn("pending", str(ctx.exception))

    def test_cannot_execute_rejected_request(self):
        approval_id = self._create_approved_request()
        # Reset to rejected
        self.approval_repo._requests[approval_id].status = ApprovalStatus.REJECTED

        with self.assertRaises(InvalidExecutionStateError) as ctx:
            self.execution_service.execute_approval(approval_id)
        self.assertIn("rejected", str(ctx.exception))

    def test_cannot_execute_already_executed_request(self):
        approval_id = self._create_approved_request()
        self.execution_service.execute_approval(approval_id)

        # Second execution attempt
        with self.assertRaises(InvalidExecutionStateError) as ctx:
            self.execution_service.execute_approval(approval_id)
        self.assertIn("executed", str(ctx.exception))

    def test_duplicate_execution_prevented_by_task_lookup(self):
        approval_id = self._create_approved_request()
        self.execution_service.execute_approval(approval_id)

        # Force approval status back to approved to test task-level idempotency
        self.approval_repo._requests[approval_id].status = ApprovalStatus.APPROVED

        with self.assertRaises(DuplicateExecutionError):
            self.execution_service.execute_approval(approval_id)

    def test_failure_handling_does_not_mark_approval_executed(self):
        approval_id = self._create_approved_request()

        # Simulate persistence failure in task repository
        self.task_repo.simulate_persistence_failure = True

        with self.assertRaises(TaskPersistenceError):
            self.execution_service.execute_approval(approval_id)

        # Ensure approval request remains in APPROVED state
        approval = self.approval_repo.get_request(approval_id)
        self.assertEqual(approval.status, ApprovalStatus.APPROVED)


if __name__ == "__main__":
    unittest.main()
