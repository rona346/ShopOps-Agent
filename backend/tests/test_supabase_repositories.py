"""
Unit and Integration Tests for Supabase PostgreSQL Repositories.
Verifies SupabaseInventoryService, SupabaseApprovalService, and SupabaseTaskService
with PostgreSQL constraint enforcement, idempotency, and non-destructive execution invariants.
"""

from datetime import datetime, timezone
import unittest
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

from app.core.supabase import (
    SupabaseDatabaseClient,
    SupabaseQueryError,
)
from app.models.approval import (
    ApprovalActionType,
    ApprovalRequestCreate,
    ApprovalStatus,
)
from app.models.inventory import (
    ProductCreate,
    ProductUpdate,
)
from app.models.task import (
    ReorderTaskCreate,
    TaskStatus,
)
from app.services.approval import (
    ApprovalNotFoundError,
    InvalidStateTransitionError,
    NoReorderNeededError,
)
from app.services.execution import (
    ActionExecutionService,
    DuplicateExecutionError,
    TaskNotFoundError,
)
from app.services.inventory import (
    DuplicateSKUError,
    ProductNotFoundError,
)
from app.services.inventory_analysis import InventoryAnalysisService
from app.services.supabase_approval import SupabaseApprovalService
from app.services.supabase_inventory import SupabaseInventoryService
from app.services.supabase_task import SupabaseTaskService


class MockSupabaseClient(SupabaseDatabaseClient):
    """
    In-memory simulation of Supabase PostgREST client enforcing PostgreSQL schema constraints:
    - uq_inventory_sku on inventory_products
    - uq_reorder_tasks_approval_id on reorder_tasks
    """

    def __init__(self):
        super().__init__(base_url="https://mock.supabase.co", service_role_key="mock-key")
        self.tables: Dict[str, Dict[str, Dict[str, Any]]] = {
            "inventory_products": {},
            "approval_requests": {},
            "reorder_tasks": {},
        }
        self._id_counter = 0

    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self._id_counter += 1
        row_id = data.get("id") or f"mock_{table}_{self._id_counter}"
        row = dict(data)
        row["id"] = row_id

        # Enforce unique constraints
        if table == "inventory_products":
            sku = row.get("sku", "").upper()
            for existing in self.tables[table].values():
                if existing.get("sku", "").upper() == sku:
                    raise SupabaseQueryError(
                        f"duplicate key value violates unique constraint 'uq_inventory_sku'",
                        status_code=409,
                        details={"code": "23505", "message": "duplicate key value violates unique constraint 'uq_inventory_sku'"},
                    )

        if table == "reorder_tasks":
            approval_id = row.get("approval_id")
            for existing in self.tables[table].values():
                if existing.get("approval_id") == approval_id:
                    raise SupabaseQueryError(
                        f"duplicate key value violates unique constraint 'uq_reorder_tasks_approval_id'",
                        status_code=409,
                        details={"code": "23505", "message": "duplicate key value violates unique constraint 'uq_reorder_tasks_approval_id'"},
                    )

        now_str = datetime.now(timezone.utc).isoformat()
        row.setdefault("created_at", now_str)
        row.setdefault("updated_at", now_str)

        self.tables[table][row_id] = row
        return row

    def get_by_id(self, table: str, row_id: str) -> Optional[Dict[str, Any]]:
        row = self.tables[table].get(row_id)
        return dict(row) if row else None

    def select(
        self,
        table: str,
        params: Optional[Dict[str, str]] = None,
        limit: int = 50,
        offset: int = 0,
        order: Optional[str] = "created_at.desc",
    ) -> Tuple[List[Dict[str, Any]], int]:
        all_rows = list(self.tables[table].values())

        if params:
            filtered = []
            for r in all_rows:
                match = True
                for k, v in params.items():
                    if v.startswith("eq."):
                        expected = v[3:]
                        if str(r.get(k)) != expected:
                            match = False
                            break
                if match:
                    filtered.append(r)
            all_rows = filtered

        # Sort newest first
        all_rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        total = len(all_rows)
        return [dict(r) for r in all_rows[offset : offset + limit]], total

    def update(self, table: str, row_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if row_id not in self.tables[table]:
            raise SupabaseQueryError(f"Row '{row_id}' not found", status_code=404)

        current = self.tables[table][row_id]
        if table == "inventory_products" and "sku" in data:
            new_sku = data["sku"].upper()
            for eid, existing in self.tables[table].items():
                if eid != row_id and existing.get("sku", "").upper() == new_sku:
                    raise SupabaseQueryError(
                        "duplicate key value violates unique constraint 'uq_inventory_sku'",
                        status_code=409,
                        details={"code": "23505"},
                    )

        current.update(data)
        current["updated_at"] = datetime.now(timezone.utc).isoformat()
        return dict(current)

    def delete(self, table: str, row_id: str) -> None:
        if row_id not in self.tables[table]:
            raise SupabaseQueryError(f"Row '{row_id}' not found", status_code=404)
        del self.tables[table][row_id]


class TestSupabaseRepositories(unittest.TestCase):
    """Test suite verifying Supabase repository operations and business invariants."""

    def setUp(self):
        self.mock_client = MockSupabaseClient()
        self.inventory_service = SupabaseInventoryService(client=self.mock_client)
        self.analysis_service = InventoryAnalysisService(inventory_service=self.inventory_service)
        self.approval_service = SupabaseApprovalService(
            inventory_service=self.inventory_service,
            analysis_service=self.analysis_service,
            client=self.mock_client,
        )
        self.task_service = SupabaseTaskService(client=self.mock_client)
        self.execution_service = ActionExecutionService(
            approval_service=self.approval_service,
            task_service=self.task_service,
            inventory_service=self.inventory_service,
        )

    # ----------------------------------------------------
    # Inventory Service Tests
    # ----------------------------------------------------
    def test_create_and_get_product(self):
        prod_in = ProductCreate(
            name="Organic Almond Milk 1L",
            sku="MILK-ALM-001",
            category="Dairy Alternatives",
            quantity=25,
            reorder_point=10,
            unit="carton",
            unit_cost=3.50,
            supplier_name="NutriDrinks Ltd",
        )
        product = self.inventory_service.create_product(prod_in)
        self.assertIsNotNone(product.id)
        self.assertEqual(product.name, "Organic Almond Milk 1L")
        self.assertEqual(product.sku, "MILK-ALM-001")
        self.assertFalse(product.is_low_stock)

        fetched = self.inventory_service.get_product(product.id)
        self.assertEqual(fetched.id, product.id)
        self.assertEqual(fetched.quantity, 25)

    def test_duplicate_sku_rejection(self):
        prod_in = ProductCreate(
            name="Item A",
            sku="DUPLICATE-SKU",
            category="General",
            quantity=10,
        )
        self.inventory_service.create_product(prod_in)

        prod_in_dup = ProductCreate(
            name="Item B",
            sku="duplicate-sku",  # normalized to DUPLICATE-SKU
            category="General",
            quantity=5,
        )
        with self.assertRaises(DuplicateSKUError):
            self.inventory_service.create_product(prod_in_dup)

    def test_update_product_and_sku_collision(self):
        p1 = self.inventory_service.create_product(
            ProductCreate(name="Item 1", sku="SKU-ONE", category="Gen", quantity=10)
        )
        p2 = self.inventory_service.create_product(
            ProductCreate(name="Item 2", sku="SKU-TWO", category="Gen", quantity=10)
        )

        # Valid update
        updated = self.inventory_service.update_product(
            p1.id, ProductUpdate(quantity=4)  # Now low stock (<= 10)
        )
        self.assertEqual(updated.quantity, 4)
        self.assertTrue(updated.is_low_stock)

        # SKU collision attempt
        with self.assertRaises(DuplicateSKUError):
            self.inventory_service.update_product(p1.id, ProductUpdate(sku="SKU-TWO"))

    def test_delete_product(self):
        p = self.inventory_service.create_product(
            ProductCreate(name="Temp Item", sku="TEMP-001", category="Gen", quantity=10)
        )
        self.inventory_service.delete_product(p.id)
        with self.assertRaises(ProductNotFoundError):
            self.inventory_service.get_product(p.id)

    # ----------------------------------------------------
    # Approval Service Tests
    # ----------------------------------------------------
    def test_approval_lifecycle(self):
        p = self.inventory_service.create_product(
            ProductCreate(name="Low Stock Item", sku="LOW-001", category="Gen", quantity=3, reorder_point=10)
        )
        # 1. Create from recommendation
        appr = self.approval_service.create_from_recommendation(p.id)
        self.assertEqual(appr.status, ApprovalStatus.PENDING)
        self.assertGreater(appr.proposed_reorder_quantity, 0)

        # 2. Modify proposed quantity
        modified = self.approval_service.update_proposed_quantity(appr.id, new_quantity=20, notes="Adjusted by owner")
        self.assertEqual(modified.proposed_reorder_quantity, 20)
        self.assertEqual(modified.owner_notes, "Adjusted by owner")

        # 3. Approve request
        approved = self.approval_service.approve_request(appr.id, notes="Approved for order")
        self.assertEqual(approved.status, ApprovalStatus.APPROVED)
        self.assertIsNotNone(approved.decided_at)

        # 4. Cannot edit after approval
        with self.assertRaises(InvalidStateTransitionError):
            self.approval_service.update_proposed_quantity(appr.id, 25)

    def test_healthy_stock_raises_no_reorder_needed(self):
        p = self.inventory_service.create_product(
            ProductCreate(name="Healthy Item", sku="HEALTHY-001", category="Gen", quantity=50, reorder_point=10)
        )
        with self.assertRaises(NoReorderNeededError):
            self.approval_service.create_from_recommendation(p.id)

    # ----------------------------------------------------
    # Task Execution & Invariant Verification Tests
    # ----------------------------------------------------
    def test_execution_creates_task_and_preserves_stock_invariant(self):
        """Verify complete approved -> executed workflow and stock preservation invariant."""
        p = self.inventory_service.create_product(
            ProductCreate(name="Critical Stock Item", sku="CRIT-001", category="Gen", quantity=2, reorder_point=15)
        )
        appr = self.approval_service.create_from_recommendation(p.id)
        self.approval_service.approve_request(appr.id)

        # Execute approval
        task = self.execution_service.execute_approval(appr.id)
        self.assertIsNotNone(task.id)
        self.assertEqual(task.approval_id, appr.id)
        self.assertEqual(task.status, TaskStatus.CREATED)

        # Verify approval marked EXECUTED
        appr_after = self.approval_service.get_request(appr.id)
        self.assertEqual(appr_after.status, ApprovalStatus.EXECUTED)

        # CRITICAL INVARIANT: On-hand inventory MUST NOT be mutated by reorder execution
        p_after = self.inventory_service.get_product(p.id)
        self.assertEqual(p_after.quantity, 2, "On-hand inventory quantity must not be mutated during reorder task creation!")

        # IDEMPOTENCY: Executing again must be rejected because approval is now 'executed'
        from app.services.execution import InvalidExecutionStateError
        with self.assertRaises(InvalidExecutionStateError):
            self.execution_service.execute_approval(appr.id)

        # Database constraint idempotency: Cannot create another task with same approval_id
        with self.assertRaises(DuplicateExecutionError):
            self.task_service.create_task(
                ReorderTaskCreate(
                    approval_id=appr.id,
                    product_id=p.id,
                    sku=p.sku,
                    product_name=p.name,
                    approved_reorder_quantity=10,
                )
            )


if __name__ == "__main__":
    unittest.main()
