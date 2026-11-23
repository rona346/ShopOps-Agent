"""
Pydantic Schemas for Internal Reorder Tasks.
Resulting from approved operational decisions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    """Lifecycle state of an internal reorder task."""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReorderTaskBase(BaseModel):
    """Core attributes of an internal reorder task."""
    approval_id: str = Field(..., description="Source approval request document ID")
    product_id: str = Field(..., description="Target inventory product document ID")
    sku: str = Field(..., description="Stock Keeping Unit")
    product_name: str = Field(..., description="Product name")
    approved_reorder_quantity: int = Field(
        ..., ge=0, description="Approved replenishment units"
    )
    estimated_cost: Optional[float] = Field(
        default=None, ge=0.0, description="Estimated total cost for reorder task"
    )
    notes: Optional[str] = Field(
        default=None, max_length=500, description="Task notes or execution details"
    )


class ReorderTaskCreate(ReorderTaskBase):
    """Schema for internal creation of a reorder task."""
    pass


class ReorderTask(ReorderTaskBase):
    """Domain model stored in Firestore collection 'reorder_tasks'."""
    id: str = Field(..., description="Unique reorder task document ID")
    status: TaskStatus = Field(
        default=TaskStatus.CREATED, description="Current execution state"
    )
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> datetime:
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


class ReorderTaskResponse(BaseModel):
    """API response schema for a reorder task."""
    id: str
    approval_id: str
    product_id: str
    sku: str
    product_name: str
    approved_reorder_quantity: int
    estimated_cost: Optional[float]
    status: TaskStatus
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, task: ReorderTask) -> "ReorderTaskResponse":
        return cls(
            id=task.id,
            approval_id=task.approval_id,
            product_id=task.product_id,
            sku=task.sku,
            product_name=task.product_name,
            approved_reorder_quantity=task.approved_reorder_quantity,
            estimated_cost=task.estimated_cost,
            status=task.status,
            notes=task.notes,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )


class ReorderTaskListResponse(BaseModel):
    """API response schema for paginated reorder tasks."""
    items: List[ReorderTaskResponse]
    total: int
    limit: int
    offset: int
