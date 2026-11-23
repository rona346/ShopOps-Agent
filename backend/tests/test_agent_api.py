"""
API Integration tests for AI Agent endpoints (/api/v1/agent/insights and /query).
Uses FastAPI TestClient, in-memory repository, and MockGeminiClient.
"""

import json
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import AuthenticatedUser, get_current_user
from app.services.agent import (
    InventoryAgentService,
    get_inventory_agent_service,
)
from app.services.inventory import get_inventory_service
from app.services.inventory_analysis import InventoryAnalysisService
from tests.fake_inventory_repo import InMemoryInventoryRepository
from tests.mock_gemini_client import MockGeminiClient


class TestInventoryAgentAPI(unittest.TestCase):
    """Test suite for agent API endpoints with mocked Gemini backend."""

    @classmethod
    def setUpClass(cls):
        cls.fake_repo = InMemoryInventoryRepository()
        cls.mock_client = MockGeminiClient()
        cls.analysis_service = InventoryAnalysisService(inventory_service=cls.fake_repo)

        # Wire mocked services into dependency overrides
        app.dependency_overrides[get_inventory_service] = lambda: cls.fake_repo
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            uid="test_owner", email="owner@shopops.local", role="owner"
        )
        app.dependency_overrides[get_inventory_agent_service] = (
            lambda: InventoryAgentService(
                analysis_service=cls.analysis_service,
                gemini_client_provider=lambda: cls.mock_client,
            )
        )
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def setUp(self):
        self.fake_repo.clear()
        # Seed test product
        self.client.post(
            "/api/v1/inventory",
            json={
                "name": "Matcha Powder",
                "sku": "TEA-MAT",
                "category": "Beverages",
                "quantity": 2,
                "reorder_point": 10,
                "unit_cost": 22.0,
            },
        )

    @patch("app.core.gemini.is_gemini_configured", return_value=True)
    def test_get_insights_endpoint(self, mock_is_configured):
        mock_response = {
            "summary": "Matcha Powder is at low stock and requires attention.",
            "critical_alerts": ["TEA-MAT (Matcha Powder) is low (2 remaining)."],
            "reorder_advice": "Reorder 18 units to maintain operating inventory.",
            "overstock_advice": None,
            "action_items": ["Order 18 units of Matcha Powder."],
        }
        self.mock_client.set_response(json.dumps(mock_response))

        res = self.client.get("/api/v1/agent/insights")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["summary"], mock_response["summary"])
        self.assertEqual(len(data["critical_alerts"]), 1)
        self.assertEqual(len(data["action_items"]), 1)

    @patch("app.core.gemini.is_gemini_configured", return_value=True)
    def test_post_query_endpoint(self, mock_is_configured):
        mock_response = {
            "answer": "Matcha Powder is currently low on stock with only 2 units remaining.",
            "relevant_skus": ["TEA-MAT"],
            "referenced_metrics": {"current_quantity": 2, "reorder_point": 10},
            "suggested_followups": ["What is the replenishment cost for TEA-MAT?"],
        }
        self.mock_client.set_response(json.dumps(mock_response))

        res = self.client.post(
            "/api/v1/agent/query",
            json={"query": "How is my matcha inventory doing?"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["answer"], mock_response["answer"])
        self.assertEqual(data["relevant_skus"], ["TEA-MAT"])

    def test_query_validation_error_on_empty_text(self):
        res = self.client.post(
            "/api/v1/agent/query",
            json={"query": "   "},
        )
        self.assertEqual(res.status_code, 422)

    @patch("app.core.gemini.is_gemini_configured", return_value=False)
    def test_insights_returns_503_when_unconfigured(self, mock_is_configured):
        res = self.client.get("/api/v1/agent/insights")
        self.assertEqual(res.status_code, 503)
        self.assertIn("not configured", res.json()["detail"].lower())

    @patch("app.core.gemini.is_gemini_configured", return_value=True)
    def test_gemini_error_returns_502(self, mock_is_configured):
        self.mock_client.set_error(RuntimeError("API quota exhausted"))
        res = self.client.get("/api/v1/agent/insights")
        self.assertEqual(res.status_code, 502)
        self.assertIn("quota exhausted", res.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
