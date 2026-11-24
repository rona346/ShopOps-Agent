"""
Supabase PostgreSQL Approval Service and Repository Implementation.
Fulfills ApprovalServiceInterface using Supabase PostgREST database operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.supabase import (
    SupabaseDatabaseClient,
    SupabaseQueryError,
    get_supabase_client,
)
from app.models.approval import (
    ApprovalRequest,
    ApprovalRequestCreate,
    ApprovalStatus,
)
from app.services.approval import (
    ApprovalNotFoundError,
    ApprovalServiceError,
    ApprovalServiceInterface,
    InvalidStateTransitionError,
    NoReorderNeededError,
)
from app.services.inventory import InventoryServiceInterface
from app.services.inventory_analysis import InventoryAnalysisService


class SupabaseApprovalService(ApprovalServiceInterface):
    """
    Production approval service utilizing Supabase PostgreSQL table 'approval_requests'.
    Persists approval rows and manages the human-in-the-loop approval lifecycle.
    """

    TABLE_NAME = "approval_requests"

    def __init__(
        self,
        inventory_service: InventoryServiceInterface,
        analysis_service: InventoryAnalysisService,
        client: Optional[SupabaseDatabaseClient] = None,
    ):
        self.inventory_service = inventory_service
        self.analysis_service = analysis_service
        self._client = client

    def _get_client(self) -> SupabaseDatabaseClient:
        if self._client is not None:
            return self._client
        return get_supabase_client()

    def create_request(self, request_in: ApprovalRequestCreate) -> ApprovalRequest:
        client = self._get_client()
        # Verify product exists in catalog
        self.inventory_service.get_product(request_in.product_id)

        now = datetime.now(timezone.utc)
        doc_data = request_in.model_dump()
        doc_data["action_type"] = request_in.action_type.value
        doc_data["status"] = ApprovalStatus.PENDING.value
        doc_data["owner_notes"] = None
        doc_data["decided_at"] = None
        doc_data["created_at"] = now.isoformat()
        doc_data["updated_at"] = now.isoformat()

        try:
            row = client.insert(self.TABLE_NAME, doc_data)
            return ApprovalRequest(**row)
        except SupabaseQueryError as exc:
            raise ApprovalServiceError(f"Failed to create approval request: {str(exc)}") from exc

    def create_from_recommendation(self, product_id: str) -> ApprovalRequest:
        product = self.inventory_service.get_product(product_id)
        analysis_item = self.analysis_service.analyze_product(product)

        if analysis_item.recommended_reorder_quantity <= 0:
            raise NoReorderNeededError(
                f"Product '{product.name}' (SKU: {product.sku}) has a recommended reorder quantity "
                f"of 0. Stock level ({product.quantity}) is healthy or overstocked."
            )

        from app.models.approval import ApprovalActionType
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
        client = self._get_client()
        params: Dict[str, str] = {}
        if status is not None:
            params["status"] = f"eq.{status.value}"

        rows, total = client.select(
            self.TABLE_NAME,
            params=params if params else None,
            limit=limit,
            offset=offset,
            order="created_at.desc",
        )
        return [ApprovalRequest(**r) for r in rows], total

    def get_request(self, request_id: str) -> ApprovalRequest:
        client = self._get_client()
        row = client.get_by_id(self.TABLE_NAME, request_id)
        if not row:
            raise ApprovalNotFoundError(f"Approval request with ID '{request_id}' was not found.")
        return ApprovalRequest(**row)

    def update_proposed_quantity(
        self, request_id: str, new_quantity: int, notes: Optional[str] = None
    ) -> ApprovalRequest:
        req = self.get_request(request_id)
        if req.status != ApprovalStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Cannot modify proposed quantity for approval request '{request_id}' "
                f"with status '{req.status.value}'. Only 'pending' requests can be modified."
            )

        client = self._get_client()
        now = datetime.now(timezone.utc)
        update_data = {
            "proposed_reorder_quantity": new_quantity,
            "updated_at": now.isoformat(),
        }
        if notes is not None:
            update_data["owner_notes"] = notes

        row = client.update(self.TABLE_NAME, request_id, update_data)
        return ApprovalRequest(**row)

    def approve_request(
        self, request_id: str, notes: Optional[str] = None
    ) -> ApprovalRequest:
        req = self.get_request(request_id)
        if req.status != ApprovalStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Cannot approve request '{request_id}' with status '{req.status.value}'. "
                f"Only 'pending' requests can be approved."
            )

        client = self._get_client()
        now = datetime.now(timezone.utc)
        update_data = {
            "status": ApprovalStatus.APPROVED.value,
            "decided_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        if notes is not None:
            update_data["owner_notes"] = notes

        row = client.update(self.TABLE_NAME, request_id, update_data)
        return ApprovalRequest(**row)

    def reject_request(
        self, request_id: str, notes: Optional[str] = None
    ) -> ApprovalRequest:
        req = self.get_request(request_id)
        if req.status != ApprovalStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Cannot reject request '{request_id}' with status '{req.status.value}'. "
                f"Only 'pending' requests can be rejected."
            )

        client = self._get_client()
        now = datetime.now(timezone.utc)
        update_data = {
            "status": ApprovalStatus.REJECTED.value,
            "decided_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        if notes is not None:
            update_data["owner_notes"] = notes

        row = client.update(self.TABLE_NAME, request_id, update_data)
        return ApprovalRequest(**row)

    def mark_executed(self, request_id: str) -> ApprovalRequest:
        req = self.get_request(request_id)
        if req.status != ApprovalStatus.APPROVED:
            raise InvalidStateTransitionError(
                f"Cannot mark request '{request_id}' as executed with status '{req.status.value}'. "
                f"Only 'approved' requests can be transitioned to 'executed'."
            )

        client = self._get_client()
        now = datetime.now(timezone.utc)
        update_data = {
            "status": ApprovalStatus.EXECUTED.value,
            "updated_at": now.isoformat(),
        }
        row = client.update(self.TABLE_NAME, request_id, update_data)
        return ApprovalRequest(**row)
