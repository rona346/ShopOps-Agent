"""
Supabase PostgreSQL Reorder Task Service and Repository Implementation.
Fulfills TaskServiceInterface using Supabase PostgREST database operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.supabase import (
    SupabaseDatabaseClient,
    SupabaseQueryError,
    get_supabase_client,
)
from app.models.task import (
    ReorderTask,
    ReorderTaskCreate,
    TaskStatus,
)
from app.services.execution import (
    DuplicateExecutionError,
    ExecutionError,
    TaskNotFoundError,
    TaskServiceInterface,
)


class SupabaseTaskService(TaskServiceInterface):
    """
    Production reorder task service utilizing Supabase PostgreSQL table 'reorder_tasks'.
    Ensures strict idempotency through unique approval_id constraints.
    """

    TABLE_NAME = "reorder_tasks"

    def __init__(self, client: Optional[SupabaseDatabaseClient] = None):
        self._client = client

    def _get_client(self) -> SupabaseDatabaseClient:
        if self._client is not None:
            return self._client
        return get_supabase_client()

    def create_task(self, task_in: ReorderTaskCreate) -> ReorderTask:
        client = self._get_client()

        # Idempotency pre-check
        existing = self.get_task_by_approval_id(task_in.approval_id)
        if existing:
            raise DuplicateExecutionError(
                f"Approval request '{task_in.approval_id}' has already been executed into task '{existing.id}'."
            )

        now = datetime.now(timezone.utc)
        doc_data = task_in.model_dump()
        doc_data["status"] = TaskStatus.CREATED.value
        doc_data["created_at"] = now.isoformat()
        doc_data["updated_at"] = now.isoformat()

        try:
            row = client.insert(self.TABLE_NAME, doc_data)
            return ReorderTask(**row)
        except SupabaseQueryError as exc:
            msg = str(exc).lower()
            if "23505" in msg or "uq_reorder_tasks_approval_id" in msg or "duplicate" in msg:
                raise DuplicateExecutionError(
                    f"Approval request '{task_in.approval_id}' has already been executed."
                ) from exc
            raise ExecutionError(f"Failed to create reorder task: {str(exc)}") from exc

    def get_task(self, task_id: str) -> ReorderTask:
        client = self._get_client()
        row = client.get_by_id(self.TABLE_NAME, task_id)
        if not row:
            raise TaskNotFoundError(f"Reorder task with ID '{task_id}' was not found.")
        return ReorderTask(**row)

    def get_task_by_approval_id(self, approval_id: str) -> Optional[ReorderTask]:
        client = self._get_client()
        rows, _ = client.select(
            self.TABLE_NAME,
            params={"approval_id": f"eq.{approval_id}"},
            limit=1,
        )
        if rows:
            return ReorderTask(**rows[0])
        return None

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ReorderTask], int]:
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
        return [ReorderTask(**r) for r in rows], total
