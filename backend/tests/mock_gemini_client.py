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

    def generate_content(
        self, model: str, contents: str, config: Any = None
    ) -> MockGenerateContentResponse:
        self.last_call = {
            "model": model,
            "contents": contents,
            "config": config,
        }
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

    def set_error(self, exception: Exception) -> None:
        self.models.exception_to_raise = exception
