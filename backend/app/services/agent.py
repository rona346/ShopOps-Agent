"""
Gemini AI Agent Engine Service for ShopOps.
Consumes structured, deterministic inventory analysis and produces business insights
and natural language Q&A. Strictly read-only; cannot write to database or execute actions.
"""

import json
from typing import Any, Callable, Dict, Optional
from fastapi import Depends
from google.genai import types
from app.core import gemini
from app.core.config import settings
from app.models.agent import (
    AgentQueryResponse,
    InventoryInsightsResponse,
)
from app.services.inventory_analysis import (
    InventoryAnalysisService,
    get_inventory_analysis_service,
)


class AgentServiceError(Exception):
    """Base exception for AI Agent operations."""
    pass


class GeminiUnavailableError(AgentServiceError):
    """Raised when the Gemini API key is missing or unconfigured."""
    pass


class GeminiServiceError(AgentServiceError):
    """Raised when an error occurs during Gemini generation or response parsing."""
    pass


class InventoryAgentService:
    """
    AI Operations Assistant powered by Google Gemini.
    Strict safety guarantees:
    - Zero write access to database or storage.
    - Grounded exclusively in deterministic inventory analysis results.
    - Cannot alter deterministic quantities or reorder points.
    - Gracefully handles missing keys and model failures.
    """

    def __init__(
        self,
        analysis_service: InventoryAnalysisService,
        gemini_client_provider: Callable[[], Any] = gemini.get_gemini_client,
    ):
        self.analysis_service = analysis_service
        self.get_client = gemini_client_provider

    def _ensure_gemini_configured(self) -> None:
        if not gemini.is_gemini_configured():
            raise GeminiUnavailableError(
                "Gemini AI service is not configured. "
                "Please set GEMINI_API_KEY in backend/.env before invoking AI agent features."
            )

    def generate_inventory_insights(
        self, category: Optional[str] = None
    ) -> InventoryInsightsResponse:
        """
        Generate executive operational insights for the retail shop owner
        using deterministic inventory analysis data as ground truth.
        """
        self._ensure_gemini_configured()

        # Step 1: Obtain deterministic ground-truth analysis
        analysis = self.analysis_service.analyze_inventory(category=category)

        # Prepare context payload
        context_data = {
            "catalog_overview": {
                "total_products": analysis.total_products,
                "total_inventory_units": analysis.total_inventory_units,
                "out_of_stock_count": analysis.out_of_stock_count,
                "low_stock_count": analysis.low_stock_count,
                "normal_stock_count": analysis.normal_stock_count,
                "overstock_count": analysis.overstock_count,
                "total_recommended_reorder_units": analysis.total_recommended_reorder_units,
                "estimated_total_reorder_cost": analysis.estimated_total_reorder_cost,
            },
            "items": [
                {
                    "sku": item.sku,
                    "name": item.name,
                    "category": item.category,
                    "quantity": item.current_quantity,
                    "reorder_point": item.reorder_point,
                    "unit": item.unit,
                    "unit_cost": item.unit_cost,
                    "status": item.status.value,
                    "recommended_reorder_quantity": item.recommended_reorder_quantity,
                    "estimated_reorder_cost": item.estimated_reorder_cost,
                    "deterministic_reason": item.reason,
                }
                for item in analysis.items
            ],
        }

        system_instruction = (
            "You are ShopOps Agent, an AI operations advisor for small retail businesses. "
            "Your task is to analyze the provided deterministic inventory status and deliver concise, "
            "actionable insights for the store owner. "
            "RULES: "
            "1. Ground your response strictly on the provided numbers; NEVER invent products or alter recommended quantities. "
            "2. Highlight out-of-stock items as urgent priority. "
            "3. Explain the business importance of reorders and warn if overstock is tying up cash. "
            "4. Respond with valid JSON matching the exact schema."
        )

        prompt = (
            f"Here is the store's current deterministic inventory analysis:\n"
            f"{json.dumps(context_data, indent=2)}\n\n"
            f"Provide an executive summary, critical alerts, reorder guidance, overstock advice, and "
            f"top action items for the owner today."
        )

        client = self.get_client()

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
        except Exception as e:
            raise GeminiServiceError(f"Gemini API request failed: {str(e)}") from e

        raw_text = getattr(response, "text", "") or "{}"
        try:
            parsed = json.loads(raw_text)
            return InventoryInsightsResponse(**parsed)
        except Exception as e:
            raise GeminiServiceError(
                f"Failed to parse structured insights from Gemini response: {str(e)}"
            ) from e

    def answer_inventory_query(
        self, query: str, category: Optional[str] = None
    ) -> AgentQueryResponse:
        """
        Answer natural language questions about store inventory.
        Strictly constrained to the store's inventory records and deterministic metrics.
        """
        self._ensure_gemini_configured()

        analysis = self.analysis_service.analyze_inventory(category=category)

        context_data = {
            "summary_metrics": {
                "total_products": analysis.total_products,
                "total_inventory_units": analysis.total_inventory_units,
                "out_of_stock_count": analysis.out_of_stock_count,
                "low_stock_count": analysis.low_stock_count,
                "overstock_count": analysis.overstock_count,
                "total_recommended_reorder_units": analysis.total_recommended_reorder_units,
                "estimated_total_reorder_cost": analysis.estimated_total_reorder_cost,
            },
            "products": [
                {
                    "sku": item.sku,
                    "name": item.name,
                    "category": item.category,
                    "quantity": item.current_quantity,
                    "reorder_point": item.reorder_point,
                    "unit_cost": item.unit_cost,
                    "status": item.status.value,
                    "recommended_reorder_quantity": item.recommended_reorder_quantity,
                }
                for item in analysis.items
            ],
        }

        system_instruction = (
            "You are ShopOps Agent, an AI inventory assistant for small retail business owners. "
            "You answer questions accurately, concisely, and practically based solely on the provided "
            "inventory records and analysis. "
            "CRITICAL CONSTRAINTS: "
            "1. NEVER invent, hallucinate, or assume products, quantities, prices, or suppliers not in the data. "
            "2. If an item or attribute is not found in the inventory data, explicitly state that it does not exist in the store catalog. "
            "3. Do not promise or perform any database writes, purchases, or modifications. "
            "4. Return a valid JSON object matching the requested schema with keys: 'answer', 'relevant_skus', 'referenced_metrics', 'suggested_followups'."
        )

        prompt = (
            f"STORE INVENTORY DATA:\n"
            f"{json.dumps(context_data, indent=2)}\n\n"
            f"OWNER'S QUESTION:\n"
            f"\"{query}\"\n\n"
            f"Provide a clear answer, list any relevant SKUs mentioned, include referenced numeric metrics, "
            f"and provide 2-3 helpful follow-up questions."
        )

        client = self.get_client()

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
        except Exception as e:
            raise GeminiServiceError(f"Gemini API request failed: {str(e)}") from e

        raw_text = getattr(response, "text", "") or "{}"
        try:
            parsed = json.loads(raw_text)
            return AgentQueryResponse(**parsed)
        except Exception as e:
            raise GeminiServiceError(
                f"Failed to parse Q&A response from Gemini: {str(e)}"
            ) from e


def get_inventory_agent_service(
    analysis_service: InventoryAnalysisService = Depends(get_inventory_analysis_service),
) -> InventoryAgentService:
    """Dependency provider for InventoryAgentService."""
    return InventoryAgentService(analysis_service=analysis_service)
