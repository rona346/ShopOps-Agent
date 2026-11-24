"""
Approval Service and Repository Layer.
Handles lifecycle and persistence of owner approval requests in collection 'approval_requests'.
Decoupled from inventory mutation and action execution.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from fastapi import Depends
from app.core import firebase
from app.models.approval import (
    ApprovalActionType,
    ApprovalRequest,
    ApprovalRequestCreate,
    ApprovalStatus,
)
from app.services.inventory import (
    FirebaseUnavailableError,
    InventoryServiceInterface,
    get_inventory_service,
)
from app.services.inventory_analysis import (
    InventoryAnalysisService,
    get_inventory_analysis_service,
)


class ApprovalServiceError(Exception):
    """Base exception for approval workflow operations."""
    pass


class ApprovalNotFoundError(ApprovalServiceError):
    """Raised when an approval request cannot be found."""
    pass


class InvalidStateTransitionError(ApprovalServiceError):
    """Raised when attempting an illegal lifecycle transition on an approval request."""
    pass


class NoReorderNeededError(ApprovalServiceError):
    """Raised when attempting to create a reorder request for an item needing 0 replenishment."""
    pass


class ApprovalServiceInterface(ABC):
    """Abstract interface defining the approval repository contract."""

    @abstractmethod
    def create_request(self, request_in: ApprovalRequestCreate) -> ApprovalRequest:
        """Create and persist a new pending approval request."""
        pass

    @abstractmethod
    def create_from_recommendation(self, product_id: str) -> ApprovalRequest:
        """Create an approval request using deterministic analysis recommendation for a product."""
        pass

    @abstractmethod
    def list_requests(
        self,
        status: Optional[ApprovalStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ApprovalRequest], int]:
        """List approval requests with pagination and optional status filter."""
        pass

    @abstractmethod
    def get_request(self, request_id: str) -> ApprovalRequest:
        """Retrieve an approval request by its ID."""
        pass

    @abstractmethod
    def update_proposed_quantity(
        self, request_id: str, new_quantity: int, notes: Optional[str] = None
    ) -> ApprovalRequest:
        """Edit the proposed replenishment quantity on a pending request."""
        pass

    @abstractmethod
    def approve_request(
        self, request_id: str, notes: Optional[str] = None
    ) -> ApprovalRequest:
        """Approve a pending approval request."""
        pass

    @abstractmethod
    def reject_request(
        self, request_id: str, notes: Optional[str] = None
    ) -> ApprovalRequest:
        """Reject a pending approval request."""
        pass

    @abstractmethod
    def mark_executed(self, request_id: str) -> ApprovalRequest:
        """Mark an approved request as executed."""
        pass


class FirestoreApprovalService(ApprovalServiceInterface):
    """
    Production approval service utilizing Firebase Firestore.
    Persists approval documents to collection 'approval_requests'.
    """

    COLLECTION_NAME = "approval_requests"

    def __init__(
        self,
        inventory_service: InventoryServiceInterface,
        analysis_service: InventoryAnalysisService,
    ):
        self.inventory_service = inventory_service
        self.analysis_service = analysis_service

    def _get_db(self):
        if not firebase.is_firebase_configured():
            raise FirebaseUnavailableError(
                "Firestore service is currently unavailable. "
                "Firebase credentials are not configured in backend/.env."
            )
        try:
            return firebase.get_firestore_client()
        except Exception as e:
            raise FirebaseUnavailableError(
                "Failed to connect to Firestore for approval operations."
            ) from e

    def create_request(self, request_in: ApprovalRequestCreate) -> ApprovalRequest:
        db = self._get_db()
        now = datetime.now(timezone.utc)

        doc_data = request_in.model_dump()
        doc_data["action_type"] = doc_data["action_type"].value if hasattr(doc_data["action_type"], "value") else doc_data["action_type"]
        doc_data["status"] = ApprovalStatus.PENDING.value
        doc_data["owner_notes"] = None
        doc_data["decided_at"] = None
        doc_data["created_at"] = now.isoformat()
        doc_data["updated_at"] = now.isoformat()

        doc_ref = db.collection(self.COLLECTION_NAME).document()
        doc_ref.set(doc_data)

        return ApprovalRequest(id=doc_ref.id, **doc_data)

    def create_from_recommendation(self, product_id: str) -> ApprovalRequest:
        product = self.inventory_service.get_product(product_id)
        analysis_item = self.analysis_service.analyze_product(product)

        if analysis_item.recommended_reorder_quantity <= 0:
            raise NoReorderNeededError(
                f"Product '{product.name}' (SKU: {product.sku}) has a recommended reorder quantity "
                f"of 0. Stock level ({product.quantity}) is healthy or overstocked."
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
        db = self._get_db()
        docs = db.collection(self.COLLECTION_NAME).stream()

        matched: List[ApprovalRequest] = []
        for doc in docs:
            data = doc.to_dict() or {}
            req = ApprovalRequest(id=doc.id, **data)

            if status is not None and req.status != status:
                continue

            matched.append(req)

        # Sort newest first
        matched.sort(key=lambda r: r.created_at, reverse=True)
        total = len(matched)
        return matched[offset : offset + limit], total

    def get_request(self, request_id: str) -> ApprovalRequest:
        db = self._get_db()
        doc = db.collection(self.COLLECTION_NAME).document(request_id).get()
        if not doc.exists:
            raise ApprovalNotFoundError(f"Approval request with ID '{request_id}' was not found.")
        data = doc.to_dict() or {}
        return ApprovalRequest(id=doc.id, **data)

    def update_proposed_quantity(
        self, request_id: str, new_quantity: int, notes: Optional[str] = None
    ) -> ApprovalRequest:
        db = self._get_db()
        doc_ref = db.collection(self.COLLECTION_NAME).document(request_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ApprovalNotFoundError(f"Approval request with ID '{request_id}' was not found.")

        data = doc.to_dict() or {}
        current_status = ApprovalStatus(data.get("status", ApprovalStatus.PENDING.value))

        if current_status != ApprovalStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Cannot edit approval request in '{current_status.value}' state. "
                "Only pending requests can be modified."
            )

        now = datetime.now(timezone.utc)
        update_data = {
            "proposed_reorder_quantity": new_quantity,
            "updated_at": now.isoformat(),
        }
        if notes is not None:
            update_data["owner_notes"] = notes

        try:
            prod = self.inventory_service.get_product(data["product_id"])
            if prod.unit_cost is not None:
                update_data["estimated_cost"] = round(new_quantity * prod.unit_cost, 2)
        except Exception:
            pass

        doc_ref.update(update_data)
        data.update(update_data)
        return ApprovalRequest(id=request_id, **data)

    def approve_request(
        self, request_id: str, notes: Optional[str] = None
    ) -> ApprovalRequest:
        db = self._get_db()
        doc_ref = db.collection(self.COLLECTION_NAME).document(request_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ApprovalNotFoundError(f"Approval request with ID '{request_id}' was not found.")

        data = doc.to_dict() or {}
        current_status = ApprovalStatus(data.get("status", ApprovalStatus.PENDING.value))

        if current_status != ApprovalStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Cannot approve request with status '{current_status.value}'. "
                f"Request has already been {current_status.value}."
            )

        now = datetime.now(timezone.utc)
        update_data = {
            "status": ApprovalStatus.APPROVED.value,
            "decided_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        if notes is not None:
            update_data["owner_notes"] = notes

        doc_ref.update(update_data)
        data.update(update_data)
        return ApprovalRequest(id=request_id, **data)

    def reject_request(
        self, request_id: str, notes: Optional[str] = None
    ) -> ApprovalRequest:
        db = self._get_db()
        doc_ref = db.collection(self.COLLECTION_NAME).document(request_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ApprovalNotFoundError(f"Approval request with ID '{request_id}' was not found.")

        data = doc.to_dict() or {}
        current_status = ApprovalStatus(data.get("status", ApprovalStatus.PENDING.value))

        if current_status != ApprovalStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Cannot reject request with status '{current_status.value}'. "
                f"Request has already been {current_status.value}."
            )

        now = datetime.now(timezone.utc)
        update_data = {
            "status": ApprovalStatus.REJECTED.value,
            "decided_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        if notes is not None:
            update_data["owner_notes"] = notes

        doc_ref.update(update_data)
        data.update(update_data)
        return ApprovalRequest(id=request_id, **data)

    def mark_executed(self, request_id: str) -> ApprovalRequest:
        db = self._get_db()
        doc_ref = db.collection(self.COLLECTION_NAME).document(request_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ApprovalNotFoundError(f"Approval request with ID '{request_id}' was not found.")

        data = doc.to_dict() or {}
        current_status = ApprovalStatus(data.get("status", ApprovalStatus.PENDING.value))

        if current_status != ApprovalStatus.APPROVED:
            raise InvalidStateTransitionError(
                f"Cannot mark request '{request_id}' as executed: current status is '{current_status.value}'. "
                f"Only approved requests can be transitioned to executed."
            )

        now = datetime.now(timezone.utc)
        update_data = {
            "status": ApprovalStatus.EXECUTED.value,
            "updated_at": now.isoformat(),
        }
        doc_ref.update(update_data)
        data.update(update_data)
        return ApprovalRequest(id=request_id, **data)


def get_approval_service(
    inventory_service: InventoryServiceInterface = Depends(get_inventory_service),
    analysis_service: InventoryAnalysisService = Depends(get_inventory_analysis_service),
) -> ApprovalServiceInterface:
    """Dependency injection provider for the approval service."""
    from app.core.supabase import is_supabase_configured
    if is_supabase_configured():
        from app.services.supabase_approval import SupabaseApprovalService
        return SupabaseApprovalService(
            inventory_service=inventory_service,
            analysis_service=analysis_service,
        )
    return FirestoreApprovalService(
        inventory_service=inventory_service,
        analysis_service=analysis_service,
    )
