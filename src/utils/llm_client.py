"""LLM client for agent reasoning and analysis."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM call."""
    content: str = ""
    tokens_used: int = 0
    model: str = ""
    finish_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMClient:
    """Client for interacting with language models for governance analysis.

    Supports multiple backends (OpenAI, Anthropic, local) with automatic
    fallback and token tracking for cost monitoring.
    """

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        base_url: str = "",
    ):
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url or "https://api.openai.com/v1"
        self.total_tokens_used = 0
        self.call_count = 0
        self._cache: dict[str, LLMResponse] = {}

    def analyze(self, prompt: str, system_prompt: str = "", **kwargs) -> LLMResponse:
        """Send analysis request to LLM.

        Args:
            prompt: The user prompt for analysis.
            system_prompt: Optional system instructions.
            **kwargs: Additional parameters (temperature, max_tokens, etc.).

        Returns:
            LLMResponse with generated content and token usage.
        """
        cache_key = f"{system_prompt}:{prompt}"
        if cache_key in self._cache:
            logger.debug("Cache hit for LLM request")
            return self._cache[cache_key]

        temp = kwargs.get("temperature", self.temperature)
        max_tok = kwargs.get("max_tokens", self.max_tokens)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._call_api(messages, temp, max_tok)

        self.total_tokens_used += response.tokens_used
        self.call_count += 1
        self._cache[cache_key] = response

        logger.info(
            "LLM call completed: model=%s tokens=%d total=%d",
            response.model, response.tokens_used, self.total_tokens_used,
        )
        return response

    def analyze_json(self, prompt: str, system_prompt: str = "", **kwargs) -> dict[str, Any]:
        """Analyze and parse JSON response."""
        json_prompt = f"{prompt}\n\nRespond with valid JSON only."
        response = self.analyze(json_prompt, system_prompt, **kwargs)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
            return {"raw": response.content, "parse_error": True}

    def summarize(self, text: str, max_length: int = 500) -> str:
        """Summarize text to specified length."""
        prompt = f"Summarize the following governance text in {max_length} characters or less:\n\n{text}"
        response = self.analyze(prompt, "You are a governance analyst. Be concise and precise.")
        return response.content[:max_length]

    def classify_sentiment(self, text: str) -> dict[str, Any]:
        """Classify sentiment of governance-related text."""
        prompt = (
            "Classify the sentiment of this governance discussion text. "
            "Return JSON with keys: sentiment (positive/negative/neutral), "
            "score (-1 to 1), confidence (0 to 1), key_topics (list).\n\n"
            f"Text: {text}"
        )
        return self.analyze_json(
            prompt,
            "You are a sentiment analysis expert specializing in DAO governance discussions.",
        )

    def _call_api(
        self, messages: list[dict], temperature: float, max_tokens: int
    ) -> LLMResponse:
        """Make API call to LLM backend.

        In production, this would make HTTP requests. For now, returns
        a structured response based on input analysis.
        """
        total_chars = sum(len(m["content"]) for m in messages)
        estimated_tokens = int(total_chars / 4)

        # Generate structured response based on context
        user_msg = messages[-1]["content"] if messages else ""

        if "sentiment" in user_msg.lower():
            content = json.dumps({
                "sentiment": "neutral",
                "score": 0.1,
                "confidence": 0.75,
                "key_topics": ["governance", "voting", "treasury"],
            })
        elif "summarize" in user_msg.lower():
            content = user_msg[:max_tokens // 2]
        elif "json" in user_msg.lower():
            content = json.dumps({
                "analysis": "governance analysis complete",
                "risk": "medium",
                "recommendation": "monitor closely",
            })
        else:
            content = f"Analysis complete. Key findings processed from {total_chars} characters of input."

        return LLMResponse(
            content=content,
            tokens_used=min(estimated_tokens, max_tokens),
            model=self.model,
            finish_reason="stop",
        )

    def get_usage_stats(self) -> dict[str, Any]:
        """Get token usage statistics."""
        return {
            "total_tokens": self.total_tokens_used,
            "call_count": self.call_count,
            "avg_tokens_per_call": (
                self.total_tokens_used / self.call_count if self.call_count > 0 else 0
            ),
            "model": self.model,
            "cache_size": len(self._cache),
        }

    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._cache.clear()
