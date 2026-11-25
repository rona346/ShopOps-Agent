"""
Mock Gemini Client for Testing.
Simulates google.genai.Client without live API requests or credentials.
"""

from typing import Any, Dict, Optional


class MockGenerateContentResponse:
    """Simulates google-genai response object."""

    def __init__(self, text: str):
        self.text = text


class MockModelsService:
    """Simulates client.models service."""

    def __init__(self, default_response_json: str = "{}"):
        self.response_json = default_response_json
        self.exception_to_raise: Optional[Exception] = None
        self.last_call: Optional[Dict[str, Any]] = None
        self.call_count: int = 0
        self.side_effects: list = []

    def generate_content(
        self, model: str, contents: str, config: Any = None
    ) -> MockGenerateContentResponse:
        self.call_count += 1
        self.last_call = {
            "model": model,
            "contents": contents,
            "config": config,
        }
        if self.side_effects:
            item = self.side_effects.pop(0)
            if isinstance(item, Exception):
                raise item
            return MockGenerateContentResponse(item)
        if self.exception_to_raise:
            raise self.exception_to_raise
        return MockGenerateContentResponse(self.response_json)


class MockGeminiClient:
    """Mock client replacing genai.Client."""

    def __init__(self, default_response_json: str = "{}"):
        self.models = MockModelsService(default_response_json)

    def set_response(self, response_json: str) -> None:
        self.models.response_json = response_json
        self.models.exception_to_raise = None
        self.models.side_effects = []

    def set_error(self, exception: Exception) -> None:
        self.models.exception_to_raise = exception
        self.models.side_effects = []

    def set_side_effects(self, effects: list) -> None:
        self.models.side_effects = list(effects)
        self.models.exception_to_raise = None
