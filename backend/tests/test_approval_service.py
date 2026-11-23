"""
Unit tests for Approval Workflow Service.
Tests creation, edits, state transitions, rejection of illegal transitions, and non-destruction.
"""

import unittest
from app.models.approval import (
    ApprovalActionType,
    ApprovalRequestCreate,
    ApprovalStatus,
)
from app.models.inventory import ProductCreate
from app.services.approval import (
    ApprovalNotFoundError,
    InvalidStateTransitionError,
    NoReorderNeededError,
)
from app.services.inventory_analysis import InventoryAnalysisService
from tests.fake_approval_repo import InMemoryApprovalRepository
from tests.fake_inventory_repo import InMemoryInventoryRepository


class TestApprovalService(unittest.TestCase):
    """Test suite for approval service state machine."""

    def setUp(self):
        self.inventory_repo = InMemoryInventoryRepository()
        self.analysis_service = InventoryAnalysisService(inventory_service=self.inventory_repo)
        self.approval_service = InMemoryApprovalRepository(
            inventory_service=self.inventory_repo,
            analysis_service=self.analysis_service,
        )

        # Create low stock test product (quantity 2, reorder 10 -> needed 18)
        self.prod_low = self.inventory_repo.create_product(
            ProductCreate(
                name="Coffee Beans",
                sku="COF-01",
                category="Beverages",
                quantity=2,
                reorder_point=10,
                unit_cost=15.0,
            )
        )
        # Create healthy test product (quantity 25, reorder 10 -> needed 0)
        self.prod_healthy = self.inventory_repo.create_product(
            ProductCreate(
                name="Green Tea",
                sku="TEA-01",
                category="Beverages",
                quantity=25,
                reorder_point=10,
                unit_cost=5.0,
            )
        )

    def test_create_request_direct(self):
        req_in = ApprovalRequestCreate(
            action_type=ApprovalActionType.REORDER,
            product_id=self.prod_low.id,
            sku="COF-01",
            product_name="Coffee Beans",
            current_quantity=2,
            proposed_reorder_quantity=18,
            reason="Stock is critically low.",
            estimated_cost=270.0,
        )
        created = self.approval_service.create_request(req_in)
        self.assertTrue(created.id.startswith("appr_"))
        self.assertEqual(created.status, ApprovalStatus.PENDING)
        self.assertEqual(created.proposed_reorder_quantity, 18)
        self.assertEqual(created.estimated_cost, 270.0)
        self.assertIsNone(created.decided_at)

    def test_create_from_recommendation_success(self):
        created = self.approval_service.create_from_recommendation(self.prod_low.id)
        self.assertEqual(created.status, ApprovalStatus.PENDING)
        self.assertEqual(created.product_id, self.prod_low.id)
        self.assertEqual(created.proposed_reorder_quantity, 18)  # 20 - 2
        self.assertEqual(created.estimated_cost, 270.0)  # 18 * 15.0

    def test_create_from_recommendation_fails_when_no_reorder_needed(self):
        with self.assertRaises(NoReorderNeededError):
            self.approval_service.create_from_recommendation(self.prod_healthy.id)

    def test_edit_proposed_quantity_when_pending(self):
        req = self.approval_service.create_from_recommendation(self.prod_low.id)
        # Owner modifies quantity from 18 to 25
        updated = self.approval_service.update_proposed_quantity(
            request_id=req.id,
            new_quantity=25,
            notes="Ordering a larger buffer for seasonal rush.",
        )
        self.assertEqual(updated.proposed_reorder_quantity, 25)
        self.assertEqual(updated.owner_notes, "Ordering a larger buffer for seasonal rush.")
        # Cost recalculated: 25 * 15.0 = 375.0
        self.assertEqual(updated.estimated_cost, 375.0)

    def test_approve_pending_request(self):
        req = self.approval_service.create_from_recommendation(self.prod_low.id)
        approved = self.approval_service.approve_request(
            request_id=req.id, notes="Approved for immediate purchase."
        )
        self.assertEqual(approved.status, ApprovalStatus.APPROVED)
        self.assertIsNotNone(approved.decided_at)
        self.assertEqual(approved.owner_notes, "Approved for immediate purchase.")

        # Ensure underlying inventory was NOT modified in this phase
        prod_check = self.inventory_repo.get_product(self.prod_low.id)
        self.assertEqual(prod_check.quantity, 2)

    def test_reject_pending_request(self):
        req = self.approval_service.create_from_recommendation(self.prod_low.id)
        rejected = self.approval_service.reject_request(
            request_id=req.id, notes="Supplier out of stock."
        )
        self.assertEqual(rejected.status, ApprovalStatus.REJECTED)
        self.assertIsNotNone(rejected.decided_at)
        self.assertEqual(rejected.owner_notes, "Supplier out of stock.")

    def test_cannot_edit_already_approved_request(self):
        req = self.approval_service.create_from_recommendation(self.prod_low.id)
        self.approval_service.approve_request(req.id)

        with self.assertRaises(InvalidStateTransitionError):
            self.approval_service.update_proposed_quantity(req.id, new_quantity=30)

    def test_cannot_approve_already_approved_request(self):
        req = self.approval_service.create_from_recommendation(self.prod_low.id)
        self.approval_service.approve_request(req.id)

        with self.assertRaises(InvalidStateTransitionError):
            self.approval_service.approve_request(req.id)

    def test_cannot_reject_already_approved_request(self):
        req = self.approval_service.create_from_recommendation(self.prod_low.id)
        self.approval_service.approve_request(req.id)

        with self.assertRaises(InvalidStateTransitionError):
            self.approval_service.reject_request(req.id)

    def test_cannot_approve_already_rejected_request(self):
        req = self.approval_service.create_from_recommendation(self.prod_low.id)
        self.approval_service.reject_request(req.id)

        with self.assertRaises(InvalidStateTransitionError):
            self.approval_service.approve_request(req.id)

    def test_nonexistent_request_raises_not_found(self):
        with self.assertRaises(ApprovalNotFoundError):
            self.approval_service.get_request("non_existent_id")

        with self.assertRaises(ApprovalNotFoundError):
            self.approval_service.approve_request("non_existent_id")


if __name__ == "__main__":
    unittest.main()
