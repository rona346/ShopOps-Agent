"""
Central router for API v1 endpoints.
Registers domain modules: auth, inventory, agent, approvals, and tasks.
Protects all operational endpoints with owner authentication.
"""

from fastapi import APIRouter, Depends
from app.api.v1.endpoints import agent, approvals, auth, inventory, tasks
from app.core.auth import get_current_user

api_router = APIRouter()

# Public/status authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Protected domain routers (Require Bearer token)
api_router.include_router(
    inventory.router,
    prefix="/inventory",
    tags=["Inventory"],
    dependencies=[Depends(get_current_user)],
)
api_router.include_router(
    agent.router,
    prefix="/agent",
    tags=["AI Agent"],
    dependencies=[Depends(get_current_user)],
)
api_router.include_router(
    approvals.router,
    prefix="/approvals",
    tags=["Approvals"],
    dependencies=[Depends(get_current_user)],
)
api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["Reorder Tasks"],
    dependencies=[Depends(get_current_user)],
)
