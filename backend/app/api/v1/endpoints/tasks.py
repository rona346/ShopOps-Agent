"""
Reorder Task REST API Endpoints.
Mounted under /api/v1/tasks.
Manages internal tasks resulting from approved operational proposals.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.models.task import (
    ReorderTaskListResponse,
    ReorderTaskResponse,
    TaskStatus,
)
from app.services.execution import (
    TaskNotFoundError,
    TaskServiceInterface,
    get_task_service,
)

router = APIRouter()


@router.get(
    "",
    response_model=ReorderTaskListResponse,
    summary="List reorder tasks",
)
def list_tasks(
    status_filter: Optional[TaskStatus] = Query(
        default=None, alias="status", description="Filter by task status"
    ),
    limit: int = Query(default=50, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    task_service: TaskServiceInterface = Depends(get_task_service),
):
    """
    List internal reorder tasks with pagination and optional status filter.
    """
    items, total = task_service.list_tasks(status=status_filter, limit=limit, offset=offset)
    return ReorderTaskListResponse(
        items=[ReorderTaskResponse.from_domain(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{task_id}",
    response_model=ReorderTaskResponse,
    summary="Get reorder task by ID",
)
def get_task(
    task_id: str,
    task_service: TaskServiceInterface = Depends(get_task_service),
):
    """
    Retrieve details of an internal reorder task by its document ID. Returns 404 if not found.
    """
    task = task_service.get_task(task_id)
    return ReorderTaskResponse.from_domain(task)


@router.get(
    "/by-approval/{approval_id}",
    response_model=ReorderTaskResponse,
    summary="Get reorder task by source approval ID",
)
def get_task_by_approval(
    approval_id: str,
    task_service: TaskServiceInterface = Depends(get_task_service),
):
    """
    Retrieve the internal reorder task linked to a specific source approval ID.
    Returns 404 if no task has been created for the approval yet.
    """
    task = task_service.get_task_by_approval_id(approval_id)
    if not task:
        raise TaskNotFoundError(
            f"No reorder task found linked to approval request '{approval_id}'."
        )
    return ReorderTaskResponse.from_domain(task)
