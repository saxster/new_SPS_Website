"""
Gemini Client Wrapper ♊
Centralized access to Google's Gemini Models with Robust Error Handling.
"""

import os
import json
from typing import Dict, Any
from google import genai
from google.genai import types
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from google.api_core import exceptions

from config.manager import config
from shared.logger import get_logger

logger = get_logger("GeminiClient")


class GeminiAgent:
    def __init__(self):
        # Config is already validated by manager
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning(
                "no_api_key",
                hint="GeminiAgent initialized without API key. Generation will fail.",
            )
            # raise RuntimeError("GOOGLE_API_KEY not set") # Deferred to generate()

        self.model_name = config.get("llm.model", "gemini-3-pro-preview")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None  # Will fail if used

        self.max_retries = config.get("llm.max_retries", 3)
        self.timeout = config.get("llm.timeout", 60)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (exceptions.ResourceExhausted, exceptions.ServiceUnavailable)
        ),
    )
    def generate(
        self, prompt: str, temperature: float = None, model: str = None
    ) -> str:
        """Text generation with retries."""
        if not self.client:
            raise RuntimeError("Cannot generate: API Key missing.")

        try:
            target_model = model or self.model_name
            config_args = {}
            if temperature is not None:
                config_args["temperature"] = temperature

            response = self.client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_args)
                if config_args
                else None,
            )
            return response.text or ""
        except Exception as e:
            logger.error(
                "gemini_gen_error",
                error=str(e),
                hint="Check API key, model name, and network connectivity.",
            )
            raise e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (exceptions.ResourceExhausted, exceptions.ServiceUnavailable)
        ),
    )
    def generate_json(self, prompt: str) -> Dict[str, Any]:
        """Generates JSON output using Gemini's structured mode or manual parsing."""

        if "Return JSON" not in prompt:
            prompt += "\n\nReturn strictly valid JSON."

        try:
            # Using generation_config for JSON response
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            return json.loads(response.text or "{}")
        except Exception as e:
            logger.error(
                "gemini_json_error",
                error=str(e),
                hint="Model returned invalid JSON. Consider lowering temperature or simplifying prompt.",
            )
            # Fallback manual clean
            try:
                # We do one un-retried attempt at manual cleanup if JSON parse fails
                text = (
                    self.client.models.generate_content(
                        model=self.model_name, contents=prompt
                    ).text
                    or ""
                )
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                return json.loads(text)
            except Exception as parse_error:
                logger.error(
                    "json_fallback_failed",
                    error=str(parse_error),
                    hint="Fallback parsing failed. Ensure prompt explicitly requests strict JSON.",
                )
                return {}
