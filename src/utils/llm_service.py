"""
LLM Service wrapper for Gemini 2.0 Flash.
Provides safe structured JSON generation.
"""

import json
import re
from typing import Any, Dict, Optional

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class LLMService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = None
        self.model = "gemini-2.0-flash"

        if api_key:
            self.set_api_key(api_key)

    # ---------------------------------------------------------
    def set_api_key(self, api_key: str) -> bool:
        if not GEMINI_AVAILABLE:
            print("Gemini SDK not installed.")
            return False

        try:
            self.client = genai.Client(api_key=api_key)
            self.api_key = api_key
            return True
        except Exception as e:
            print(f"Failed to configure Gemini: {e}")
            self.client = None
            return False

    # ---------------------------------------------------------
    def is_available(self) -> bool:
        return GEMINI_AVAILABLE and self.client is not None

    # ---------------------------------------------------------
    def _generate_raw(self, full_prompt: str, temperature: float, max_tokens: int) -> str:
        if not self.is_available():
            raise RuntimeError("LLM not available — missing API key or SDK.")

        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )

            # new SDK always returns .text
            return (resp.text or "").strip()

        except Exception as e:
            raise RuntimeError(f"Gemini call failed: {e}")

    # ---------------------------------------------------------
    def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:

        # enforce JSON response
        enforce = "Return ONLY a valid JSON object or array. No extra text."
        full_prompt = ((system_prompt or "") + "\n" + enforce + "\n\n" + prompt).strip()

        raw = self._generate_raw(full_prompt, temperature, max_tokens)

        # First try strict
        try:
            return json.loads(raw)
        except:
            pass

        # Try regex extract
        match = re.search(r"\{.*\}|\[.*\]", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass

        return {"error": "invalid_json", "raw": raw}


# global instance (no key until app passes one)
llm_service = LLMService()
