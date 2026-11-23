"""
Isolated In-Memory Approval Repository for Testing.
Strictly used for unit and API tests. Never used in production.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from app.models.approval import (
    ApprovalActionType,
    ApprovalRequest,
    ApprovalRequestCreate,
    ApprovalStatus,
)
from app.services.approval import (
    ApprovalNotFoundError,
    ApprovalServiceInterface,
    InvalidStateTransitionError,
    NoReorderNeededError,
)
from app.services.inventory import InventoryServiceInterface
from app.services.inventory_analysis import InventoryAnalysisService


class InMemoryApprovalRepository(ApprovalServiceInterface):
    """Test repository implementing ApprovalServiceInterface in memory."""

    def __init__(
        self,
        inventory_service: InventoryServiceInterface,
        analysis_service: InventoryAnalysisService,
    ):
        self._requests: Dict[str, ApprovalRequest] = {}
        self.inventory_service = inventory_service
        self.analysis_service = analysis_service

    def clear(self):
        self._requests.clear()

    def create_request(self, request_in: ApprovalRequestCreate) -> ApprovalRequest:
        now = datetime.now(timezone.utc)
        request_id = f"appr_{uuid.uuid4().hex[:8]}"

        req = ApprovalRequest(
            id=request_id,
            action_type=request_in.action_type,
            product_id=request_in.product_id,
            sku=request_in.sku,
            product_name=request_in.product_name,
            current_quantity=request_in.current_quantity,
            proposed_reorder_quantity=request_in.proposed_reorder_quantity,
            reason=request_in.reason,
            estimated_cost=request_in.estimated_cost,
            status=ApprovalStatus.PENDING,
            owner_notes=None,
            decided_at=None,
            created_at=now,
            updated_at=now,
        )
        self._requests[request_id] = req
        return req

    def create_from_recommendation(self, product_id: str) -> ApprovalRequest:
        product = self.inventory_service.get_product(product_id)
        analysis_item = self.analysis_service.analyze_product(product)

        if analysis_item.recommended_reorder_quantity <= 0:
            raise NoReorderNeededError(
                f"Product '{product.name}' (SKU: {product.sku}) has a recommended reorder quantity of 0."
            )

        req_in = ApprovalRequestCreate(
            action_type=ApprovalActionType.REORDER,
            product_id=product.id,
            sku=product.sku,
            product_name=product.name,
            current_quantity=product.quantity,
            proposed_reorder_quantity=analysis_item.recommended_reorder_quantity,
            reason=analysis_item.reason,
            estimated_cost=analysis_item.estimated_reorder_cost,
        )
        return self.create_request(req_in)

    def list_requests(
        self,
        status: Optional[ApprovalStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ApprovalRequest], int]:
        items = list(self._requests.values())
        if status is not None:
            items = [r for r in items if r.status == status]

        items.sort(key=lambda r: r.created_at, reverse=True)
        total = len(items)
        return items[offset : offset + limit], total

    def get_request(self, request_id: str) -> ApprovalRequest:
        if request_id not in self._requests:
            raise ApprovalNotFoundError(f"Approval request with ID '{request_id}' was not found.")
        return self._requests[request_id]

    def update_proposed_quantity(
        self, request_id: str, new_quantity: int, notes: Optional[str] = None
    ) -> ApprovalRequest:
        if request_id not in self._requests:
            raise ApprovalNotFoundError(f"Approval request with ID '{request_id}' was not found.")

        current = self._requests[request_id]
        if current.status != ApprovalStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Cannot edit approval request in '{current.status.value}' state. Only pending requests can be modified."
            )

        now = datetime.now(timezone.utc)
        data = current.model_dump()
        data["proposed_reorder_quantity"] = new_quantity
        data["updated_at"] = now
        if notes is not None:
            data["owner_notes"] = notes

        try:
            prod = self.inventory_service.get_product(current.product_id)
            if prod.unit_cost is not None:
                data["estimated_cost"] = round(new_quantity * prod.unit_cost, 2)
        except Exception:
            pass

        updated = ApprovalRequest(**data)
        self._requests[request_id] = updated
        return updated

    def approve_request(
        self, request_id: str, notes: Optional[str] = None
    ) -> ApprovalRequest:
        if request_id not in self._requests:
            raise ApprovalNotFoundError(f"Approval request with ID '{request_id}' was not found.")

        current = self._requests[request_id]
        if current.status != ApprovalStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Cannot approve request with status '{current.status.value}'. Request has already been {current.status.value}."
            )

        now = datetime.now(timezone.utc)
        data = current.model_dump()
        data["status"] = ApprovalStatus.APPROVED
        data["decided_at"] = now
        data["updated_at"] = now
        if notes is not None:
            data["owner_notes"] = notes

        updated = ApprovalRequest(**data)
        self._requests[request_id] = updated
        return updated

    def reject_request(
        self, request_id: str, notes: Optional[str] = None
    ) -> ApprovalRequest:
        if request_id not in self._requests:
            raise ApprovalNotFoundError(f"Approval request with ID '{request_id}' was not found.")

        current = self._requests[request_id]
        if current.status != ApprovalStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Cannot reject request with status '{current.status.value}'. Request has already been {current.status.value}."
            )

        now = datetime.now(timezone.utc)
        data = current.model_dump()
        data["status"] = ApprovalStatus.REJECTED
        data["decided_at"] = now
        data["updated_at"] = now
        if notes is not None:
            data["owner_notes"] = notes

        updated = ApprovalRequest(**data)
        self._requests[request_id] = updated
        return updated

    def mark_executed(self, request_id: str) -> ApprovalRequest:
        if request_id not in self._requests:
            raise ApprovalNotFoundError(f"Approval request with ID '{request_id}' was not found.")

        current = self._requests[request_id]
        if current.status != ApprovalStatus.APPROVED:
            raise InvalidStateTransitionError(
                f"Cannot mark request '{request_id}' as executed: current status is '{current.status.value}'. "
                f"Only approved requests can be transitioned to executed."
            )

        now = datetime.now(timezone.utc)
        data = current.model_dump()
        data["status"] = ApprovalStatus.EXECUTED
        data["updated_at"] = now

        updated = ApprovalRequest(**data)
        self._requests[request_id] = updated
        return updated
