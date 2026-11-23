"""
Pydantic Schemas for the Owner Approval Workflow.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ApprovalStatus(str, Enum):
    """Lifecycle state of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class ApprovalActionType(str, Enum):
    """Categorization of proposed operational actions."""
    REORDER = "reorder"


class ApprovalRequestBase(BaseModel):
    """Core attributes of an approval request."""
    action_type: ApprovalActionType = Field(
        default=ApprovalActionType.REORDER,
        description="Type of operational action proposed",
    )
    product_id: str = Field(..., description="Target inventory product document ID")
    sku: str = Field(..., description="Stock Keeping Unit")
    product_name: str = Field(..., description="Product name")
    current_quantity: int = Field(..., ge=0, description="Quantity in stock when proposed")
    proposed_reorder_quantity: int = Field(
        ..., ge=0, description="Proposed replenishment quantity"
    )
    reason: str = Field(..., description="Deterministic or operational rationale for reorder")
    estimated_cost: Optional[float] = Field(
        default=None, ge=0.0, description="Estimated total cost for proposed reorder"
    )


class ApprovalRequestCreate(ApprovalRequestBase):
    """Schema for manually creating a reorder approval request."""
    pass


class ApprovalCreateFromRecommendation(BaseModel):
    """Schema for creating an approval request from an existing product's reorder recommendation."""
    product_id: str = Field(
        ..., min_length=1, description="Product document ID to create recommendation approval for"
    )


class ApprovalRequestUpdate(BaseModel):
    """Schema for owner editing the proposed reorder quantity before decision."""
    proposed_reorder_quantity: int = Field(
        ..., ge=0, description="Adjusted replenishment quantity"
    )
    notes: Optional[str] = Field(
        default=None, max_length=500, description="Optional owner notes regarding the modification"
    )


class ApprovalDecision(BaseModel):
    """Schema for approving or rejecting a pending request."""
    notes: Optional[str] = Field(
        default=None, max_length=500, description="Optional notes on the decision"
    )


class ApprovalRequest(ApprovalRequestBase):
    """Domain model stored in Firestore collection 'approval_requests'."""
    id: str = Field(..., description="Unique approval request ID")
    status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING, description="Current approval state"
    )
    owner_notes: Optional[str] = Field(
        default=None, description="Notes added by owner on edit, approval, or rejection"
    )
    decided_at: Optional[datetime] = Field(
        default=None, description="Timestamp when decision was finalized"
    )
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("created_at", "updated_at", "decided_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> Optional[datetime]:
        if v is None:
            return None
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
        return datetime.now(timezone.utc)


class ApprovalRequestResponse(BaseModel):
    """API response schema for an individual approval request."""
    id: str
    action_type: ApprovalActionType
    product_id: str
    sku: str
    product_name: str
    current_quantity: int
    proposed_reorder_quantity: int
    reason: str
    estimated_cost: Optional[float]
    status: ApprovalStatus
    owner_notes: Optional[str]
    decided_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, req: ApprovalRequest) -> "ApprovalRequestResponse":
        return cls(
            id=req.id,
            action_type=req.action_type,
            product_id=req.product_id,
            sku=req.sku,
            product_name=req.product_name,
            current_quantity=req.current_quantity,
            proposed_reorder_quantity=req.proposed_reorder_quantity,
            reason=req.reason,
            estimated_cost=req.estimated_cost,
            status=req.status,
            owner_notes=req.owner_notes,
            decided_at=req.decided_at,
            created_at=req.created_at,
            updated_at=req.updated_at,
        )


class ApprovalListResponse(BaseModel):
    """API response schema for paginated approval requests."""
    items: List[ApprovalRequestResponse]
    total: int
    limit: int
    offset: int
