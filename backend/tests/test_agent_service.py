"""
Unit tests for InventoryAgentService.
Tests prompt preparation, response parsing, and error handling with MockGeminiClient.
"""

import json
import unittest
from unittest.mock import patch
from app.models.inventory import ProductCreate
from app.services.agent import (
    GeminiServiceError,
    GeminiUnavailableError,
    InventoryAgentService,
)
from app.services.inventory_analysis import InventoryAnalysisService
from tests.fake_inventory_repo import InMemoryInventoryRepository
from tests.mock_gemini_client import MockGeminiClient


class TestInventoryAgentService(unittest.TestCase):
    """Test suite for AI Agent service logic and safety boundaries."""

    def setUp(self):
        self.repo = InMemoryInventoryRepository()
        self.analysis_service = InventoryAnalysisService(inventory_service=self.repo)

        # Seed sample inventory
        self.repo.create_product(
            ProductCreate(
                name="Coffee Beans",
                sku="COF-01",
                category="Beverages",
                quantity=0,
                reorder_point=10,
                unit_cost=15.0,
            )
        )
        self.repo.create_product(
            ProductCreate(
                name="Paper Napkins",
                sku="NAP-01",
                category="Supplies",
                quantity=45,
                reorder_point=10,
                unit_cost=1.5,
            )
        )

        self.mock_client = MockGeminiClient()
        self.agent_service = InventoryAgentService(
            analysis_service=self.analysis_service,
            gemini_client_provider=lambda: self.mock_client,
        )

    @patch("app.core.gemini.is_gemini_configured", return_value=True)
    def test_generate_inventory_insights_success(self, mock_is_configured):
        mock_insights = {
            "summary": "The inventory has 1 out-of-stock item and 1 overstocked item.",
            "critical_alerts": ["COF-01 (Coffee Beans) is completely out of stock."],
            "reorder_advice": "Reorder 20 units of Coffee Beans to restore target buffer.",
            "overstock_advice": "Consider promotional bundling for Paper Napkins to release working capital.",
            "action_items": [
                "Place order for 20 units of COF-01 immediately.",
                "Review supplier terms for paper goods.",
            ],
        }
        self.mock_client.set_response(json.dumps(mock_insights))

        insights = self.agent_service.generate_inventory_insights()
        self.assertEqual(insights.summary, mock_insights["summary"])
        self.assertEqual(len(insights.critical_alerts), 1)
        self.assertIn("COF-01", insights.critical_alerts[0])
        self.assertEqual(len(insights.action_items), 2)

        # Verify ground truth was sent in prompt
        last_prompt = self.mock_client.models.last_call["contents"]
        self.assertIn("COF-01", last_prompt)
        self.assertIn("Coffee Beans", last_prompt)

    @patch("app.core.gemini.is_gemini_configured", return_value=True)
    def test_answer_inventory_query_success(self, mock_is_configured):
        mock_answer = {
            "answer": "Coffee Beans (COF-01) is currently out of stock with 0 units on hand.",
            "relevant_skus": ["COF-01"],
            "referenced_metrics": {"current_quantity": 0, "reorder_point": 10},
            "suggested_followups": [
                "What is the total reorder cost for coffee?",
                "Which supplier provides COF-01?",
            ],
        }
        self.mock_client.set_response(json.dumps(mock_answer))

        response = self.agent_service.answer_inventory_query("Which items are out of stock?")
        self.assertEqual(response.answer, mock_answer["answer"])
        self.assertEqual(response.relevant_skus, ["COF-01"])
        self.assertEqual(response.referenced_metrics["current_quantity"], 0)
        self.assertEqual(len(response.suggested_followups), 2)

    @patch("app.core.gemini.is_gemini_configured", return_value=False)
    def test_unconfigured_gemini_raises_error(self, mock_is_configured):
        with self.assertRaises(GeminiUnavailableError):
            self.agent_service.generate_inventory_insights()

        with self.assertRaises(GeminiUnavailableError):
            self.agent_service.answer_inventory_query("Any stock issues?")

    @patch("app.core.gemini.is_gemini_configured", return_value=True)
    def test_gemini_api_network_error_handling(self, mock_is_configured):
        self.mock_client.set_error(RuntimeError("Connection timeout to Gemini"))

        with self.assertRaises(GeminiServiceError) as ctx:
            self.agent_service.generate_inventory_insights()
        self.assertIn("Connection timeout", str(ctx.exception))

    @patch("app.core.gemini.is_gemini_configured", return_value=True)
    def test_malformed_model_response_handling(self, mock_is_configured):
        self.mock_client.set_response("This is plain text, not valid JSON")

        with self.assertRaises(GeminiServiceError) as ctx:
            self.agent_service.generate_inventory_insights()
        self.assertIn("Failed to parse", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
