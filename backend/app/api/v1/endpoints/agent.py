"""
AI Agent REST API Endpoints.
Mounted under /api/v1/agent.
Provides executive inventory insights and grounded natural language Q&A.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.models.agent import (
    AgentQueryRequest,
    AgentQueryResponse,
    InventoryInsightsResponse,
)
from app.services.agent import (
    InventoryAgentService,
    get_inventory_agent_service,
)

router = APIRouter()


@router.get(
    "/insights",
    response_model=InventoryInsightsResponse,
    summary="Generate executive inventory insights via Gemini AI",
)
def get_insights(
    category: Optional[str] = Query(default=None, description="Filter insights by category"),
    agent_service: InventoryAgentService = Depends(get_inventory_agent_service),
):
    """
    Generate actionable business insights for the retail store owner.
    Explains out-of-stock items, replenishment priorities, and overstock risks,
    grounded strictly in deterministic inventory analysis.
    """
    return agent_service.generate_inventory_insights(category=category)


@router.post(
    "/query",
    response_model=AgentQueryResponse,
    summary="Ask a natural language question about store inventory",
)
def query_agent(
    request: AgentQueryRequest,
    agent_service: InventoryAgentService = Depends(get_inventory_agent_service),
):
    """
    Answer natural language questions about current inventory status, reorder targets,
    and product counts. Grounded exclusively in verified store catalog records.
    """
    return agent_service.answer_inventory_query(
        query=request.query, category=request.category
    )
