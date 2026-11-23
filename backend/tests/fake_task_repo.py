"""
Isolated In-Memory Reorder Task Repository for Testing.
Strictly used for unit and API tests. Never used in production.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from app.models.task import (
    ReorderTask,
    ReorderTaskCreate,
    TaskStatus,
)
from app.services.execution import (
    TaskNotFoundError,
    TaskServiceInterface,
)


class InMemoryTaskRepository(TaskServiceInterface):
    """Test repository implementing TaskServiceInterface in memory."""

    def __init__(self):
        self._tasks: Dict[str, ReorderTask] = {}
        self.simulate_persistence_failure: bool = False

    def clear(self):
        self._tasks.clear()
        self.simulate_persistence_failure = False

    def create_task(self, task_in: ReorderTaskCreate) -> ReorderTask:
        now = datetime.now(timezone.utc)
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        task = ReorderTask(
            id=task_id,
            approval_id=task_in.approval_id,
            product_id=task_in.product_id,
            sku=task_in.sku,
            product_name=task_in.product_name,
            approved_reorder_quantity=task_in.approved_reorder_quantity,
            estimated_cost=task_in.estimated_cost,
            notes=task_in.notes,
            status=TaskStatus.CREATED,
            created_at=now,
            updated_at=now,
        )

        if not self.simulate_persistence_failure:
            self._tasks[task_id] = task

        return task

    def get_task(self, task_id: str) -> ReorderTask:
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Reorder task with ID '{task_id}' was not found.")
        return self._tasks[task_id]

    def get_task_by_approval_id(self, approval_id: str) -> Optional[ReorderTask]:
        for task in self._tasks.values():
            if task.approval_id == approval_id:
                return task
        return None

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ReorderTask], int]:
        items = list(self._tasks.values())
        if status is not None:
            items = [t for t in items if t.status == status]

        items.sort(key=lambda t: t.created_at, reverse=True)
        total = len(items)
        return items[offset : offset + limit], total
