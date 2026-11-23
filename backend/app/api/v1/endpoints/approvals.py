"""
Approval REST API Endpoints.
Mounted under /api/v1/approvals.
Manages owner approval requests for proposed operations.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.models.approval import (
    ApprovalCreateFromRecommendation,
    ApprovalDecision,
    ApprovalListResponse,
    ApprovalRequestCreate,
    ApprovalRequestResponse,
    ApprovalRequestUpdate,
    ApprovalStatus,
)
from app.models.task import ReorderTaskResponse
from app.services.approval import (
    ApprovalServiceInterface,
    get_approval_service,
)
from app.services.execution import (
    ActionExecutionService,
    get_action_execution_service,
)

router = APIRouter()


@router.get(
    "",
    response_model=ApprovalListResponse,
    summary="List approval requests",
)
def list_approvals(
    status_filter: Optional[ApprovalStatus] = Query(
        default=None, alias="status", description="Filter requests by status (pending, approved, rejected, executed)"
    ),
    limit: int = Query(default=50, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    service: ApprovalServiceInterface = Depends(get_approval_service),
):
    """
    List approval requests with pagination and optional status filter.
    """
    items, total = service.list_requests(status=status_filter, limit=limit, offset=offset)
    return ApprovalListResponse(
        items=[ApprovalRequestResponse.from_domain(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ApprovalRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create approval request manually",
)
def create_approval(
    request_in: ApprovalRequestCreate,
    service: ApprovalServiceInterface = Depends(get_approval_service),
):
    """
    Create a new pending approval request with proposed reorder quantity and reason.
    """
    created = service.create_request(request_in)
    return ApprovalRequestResponse.from_domain(created)


@router.post(
    "/from-recommendation",
    response_model=ApprovalRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create approval request from deterministic reorder recommendation",
)
def create_from_recommendation(
    payload: ApprovalCreateFromRecommendation,
    service: ApprovalServiceInterface = Depends(get_approval_service),
):
    """
    Generate a pending approval request using the deterministic reorder quantity
    and rationale calculated for the given product ID.
    Fails if the product has 0 recommended reorder quantity.
    """
    created = service.create_from_recommendation(payload.product_id)
    return ApprovalRequestResponse.from_domain(created)


@router.get(
    "/{request_id}",
    response_model=ApprovalRequestResponse,
    summary="Get approval request by ID",
)
def get_approval(
    request_id: str,
    service: ApprovalServiceInterface = Depends(get_approval_service),
):
    """
    Retrieve details of an approval request by its ID. Returns 404 if not found.
    """
    req = service.get_request(request_id)
    return ApprovalRequestResponse.from_domain(req)


@router.patch(
    "/{request_id}",
    response_model=ApprovalRequestResponse,
    summary="Edit proposed quantity before decision",
)
def edit_proposed_quantity(
    request_id: str,
    payload: ApprovalRequestUpdate,
    service: ApprovalServiceInterface = Depends(get_approval_service),
):
    """
    Allow the store owner to adjust the proposed reorder quantity before deciding.
    Only permitted while the request is in 'pending' state.
    """
    updated = service.update_proposed_quantity(
        request_id=request_id,
        new_quantity=payload.proposed_reorder_quantity,
        notes=payload.notes,
    )
    return ApprovalRequestResponse.from_domain(updated)


@router.post(
    "/{request_id}/approve",
    response_model=ApprovalRequestResponse,
    summary="Approve a pending request",
)
def approve_request(
    request_id: str,
    decision: Optional[ApprovalDecision] = None,
    service: ApprovalServiceInterface = Depends(get_approval_service),
):
    """
    Approve a pending operational proposal.
    Rejects transition if request has already been approved, rejected, or executed.
    Does not automatically trigger inventory mutation or purchases.
    """
    notes = decision.notes if decision else None
    approved = service.approve_request(request_id=request_id, notes=notes)
    return ApprovalRequestResponse.from_domain(approved)


@router.post(
    "/{request_id}/reject",
    response_model=ApprovalRequestResponse,
    summary="Reject a pending request",
)
def reject_request(
    request_id: str,
    decision: Optional[ApprovalDecision] = None,
    service: ApprovalServiceInterface = Depends(get_approval_service),
):
    """
    Reject a pending operational proposal.
    Rejects transition if request has already been approved, rejected, or executed.
    """
    notes = decision.notes if decision else None
    rejected = service.reject_request(request_id=request_id, notes=notes)
    return ApprovalRequestResponse.from_domain(rejected)


@router.post(
    "/{request_id}/execute",
    response_model=ReorderTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute an approved proposal into a verified internal reorder task",
)
def execute_approval(
    request_id: str,
    execution_notes: Optional[str] = Query(default=None, description="Optional notes on execution"),
    execution_service: ActionExecutionService = Depends(get_action_execution_service),
):
    """
    Execute an approved operational proposal.
    Creates an internal reorder task, verifies its persistence, and transitions
    the approval request status to 'executed'.
    Fails if the approval is not in 'approved' status or has already been executed.
    """
    task = execution_service.execute_approval(
        approval_id=request_id, execution_notes=execution_notes
    )
    return ReorderTaskResponse.from_domain(task)
