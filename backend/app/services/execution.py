"""
Action Execution Service and Reorder Task Layer.
Coordinates execution of owner-approved requests into verified internal reorder tasks.
Does NOT modify inventory or make real external payments.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from fastapi import Depends
from app.core import firebase
from app.models.approval import ApprovalStatus
from app.models.task import (
    ReorderTask,
    ReorderTaskCreate,
    TaskStatus,
)
from app.services.approval import (
    ApprovalNotFoundError,
    ApprovalServiceInterface,
    InvalidStateTransitionError,
    get_approval_service,
)
from app.services.inventory import (
    FirebaseUnavailableError,
    InventoryServiceInterface,
    get_inventory_service,
)


class ExecutionError(Exception):
    """Base exception for action execution."""
    pass


class InvalidExecutionStateError(ExecutionError):
    """Raised when an approval request is not in 'approved' status."""
    pass


class DuplicateExecutionError(ExecutionError):
    """Raised when an approval request has already been executed into a task."""
    pass


class TaskNotFoundError(ExecutionError):
    """Raised when a reorder task ID cannot be found."""
    pass


class TaskPersistenceError(ExecutionError):
    """Raised when verification of persisted task fails."""
    pass


class TaskServiceInterface(ABC):
    """Abstract interface defining the reorder task repository contract."""

    @abstractmethod
    def create_task(self, task_in: ReorderTaskCreate) -> ReorderTask:
        """Create and persist a new reorder task."""
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> ReorderTask:
        """Retrieve a task by ID."""
        pass

    @abstractmethod
    def get_task_by_approval_id(self, approval_id: str) -> Optional[ReorderTask]:
        """Retrieve task linked to a specific source approval ID (idempotency check)."""
        pass

    @abstractmethod
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ReorderTask], int]:
        """List tasks with pagination and optional status filter."""
        pass


class FirestoreTaskService(TaskServiceInterface):
    """
    Production reorder task service utilizing Firebase Firestore collection 'reorder_tasks'.
    """

    COLLECTION_NAME = "reorder_tasks"

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
                "Failed to connect to Firestore for task operations."
            ) from e

    def create_task(self, task_in: ReorderTaskCreate) -> ReorderTask:
        db = self._get_db()
        now = datetime.now(timezone.utc)

        doc_data = task_in.model_dump()
        doc_data["status"] = TaskStatus.CREATED.value
        doc_data["created_at"] = now.isoformat()
        doc_data["updated_at"] = now.isoformat()

        doc_ref = db.collection(self.COLLECTION_NAME).document()
        doc_ref.set(doc_data)

        return ReorderTask(id=doc_ref.id, **doc_data)

    def get_task(self, task_id: str) -> ReorderTask:
        db = self._get_db()
        doc = db.collection(self.COLLECTION_NAME).document(task_id).get()
        if not doc.exists:
            raise TaskNotFoundError(f"Reorder task with ID '{task_id}' was not found.")
        data = doc.to_dict() or {}
        return ReorderTask(id=doc.id, **data)

    def get_task_by_approval_id(self, approval_id: str) -> Optional[ReorderTask]:
        db = self._get_db()
        docs = (
            db.collection(self.COLLECTION_NAME)
            .where("approval_id", "==", approval_id)
            .limit(1)
            .get()
        )
        for doc in docs:
            data = doc.to_dict() or {}
            return ReorderTask(id=doc.id, **data)
        return None

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ReorderTask], int]:
        db = self._get_db()
        docs = db.collection(self.COLLECTION_NAME).stream()

        matched: List[ReorderTask] = []
        for doc in docs:
            data = doc.to_dict() or {}
            task = ReorderTask(id=doc.id, **data)
            if status is not None and task.status != status:
                continue
            matched.append(task)

        matched.sort(key=lambda t: t.created_at, reverse=True)
        total = len(matched)
        return matched[offset : offset + limit], total


class ActionExecutionService:
    """
    Coordinates execution of approved operational proposals into verified reorder tasks.
    Guarantees:
    - Only requests with status 'approved' can be executed.
    - Idempotent: rejects duplicate executions.
    - Verification step: verifies task was stored before updating approval to 'executed'.
    - Non-destructive: does NOT modify inventory quantities in this phase.
    """

    def __init__(
        self,
        approval_service: ApprovalServiceInterface,
        task_service: TaskServiceInterface,
        inventory_service: InventoryServiceInterface,
    ):
        self.approval_service = approval_service
        self.task_service = task_service
        self.inventory_service = inventory_service

    def execute_approval(
        self, approval_id: str, execution_notes: Optional[str] = None
    ) -> ReorderTask:
        # Step 1: Retrieve approval request
        approval = self.approval_service.get_request(approval_id)

        # Step 2: Validate approval status is strictly APPROVED
        if approval.status != ApprovalStatus.APPROVED:
            raise InvalidExecutionStateError(
                f"Cannot execute approval request '{approval_id}' with status '{approval.status.value}'. "
                f"Only requests with status 'approved' can be executed."
            )

        # Step 3: Check idempotency (prevent duplicate tasks)
        existing_task = self.task_service.get_task_by_approval_id(approval_id)
        if existing_task is not None:
            raise DuplicateExecutionError(
                f"Approval request '{approval_id}' has already been executed into task '{existing_task.id}'."
            )

        # Step 4: Create ReorderTask
        task_create = ReorderTaskCreate(
            approval_id=approval.id,
            product_id=approval.product_id,
            sku=approval.sku,
            product_name=approval.product_name,
            approved_reorder_quantity=approval.proposed_reorder_quantity,
            estimated_cost=approval.estimated_cost,
            notes=execution_notes,
        )
        task = self.task_service.create_task(task_create)

        # Step 5: Verify task persistence before marking approval as executed
        try:
            persisted_task = self.task_service.get_task(task.id)
        except Exception as e:
            raise TaskPersistenceError(
                f"Verification failed: Created task '{task.id}' could not be verified in persistence layer."
            ) from e

        if not persisted_task or persisted_task.approval_id != approval_id:
            raise TaskPersistenceError(
                f"Verification failed: Created task '{task.id}' could not be verified."
            )

        # Step 6: Mark approval request as EXECUTED
        self.approval_service.mark_executed(approval_id)

        # Inventory quantity is NOT modified here; stock only updates upon goods receipt.
        return persisted_task


def get_task_service() -> TaskServiceInterface:
    """Dependency provider for TaskServiceInterface."""
    return FirestoreTaskService()


def get_action_execution_service(
    approval_service: ApprovalServiceInterface = Depends(get_approval_service),
    task_service: TaskServiceInterface = Depends(get_task_service),
    inventory_service: InventoryServiceInterface = Depends(get_inventory_service),
) -> ActionExecutionService:
    """Dependency provider for ActionExecutionService."""
    return ActionExecutionService(
        approval_service=approval_service,
        task_service=task_service,
        inventory_service=inventory_service,
    )
