"""
Google Gemini API client initialization foundation for ShopOps Agent.
Provides lazy-loaded, safe client initialization using the google-genai SDK.
"""

from typing import Optional
from google import genai
from app.core.config import settings

_gemini_client: Optional[genai.Client] = None


def is_gemini_configured() -> bool:
    """Check whether a Gemini API key is configured in settings."""
    api_key = (settings.GEMINI_API_KEY or "").strip()
    return bool(api_key and api_key not in ("", "your_gemini_api_key_here"))


def get_gemini_client() -> genai.Client:
    """
    Safely initialize and retrieve the Gemini client instance (singleton).
    Raises RuntimeError with a clear message if GEMINI_API_KEY is not configured.
    Does not make any network requests during client creation.
    """
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client

    api_key = (settings.GEMINI_API_KEY or "").strip()
    if not api_key or api_key in ("", "your_gemini_api_key_here"):
        raise RuntimeError(
            "Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env "
            "before calling AI operations."
        )

    _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client
