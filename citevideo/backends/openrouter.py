"""
Explicit fallback backend for OpenRouter-powered research or synthesis.
Disabled by default in the broader pipeline.
"""

from __future__ import annotations

from citevideo.backends.base import ResearchBackend, SynthesisBackend
from citevideo.config import get_openrouter_research_model
from citevideo.llm import openrouter_chat


class OpenRouterBackend(ResearchBackend, SynthesisBackend):
    name = "openrouter"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or get_openrouter_research_model()

    def run(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        label: str = "",
        timeout: int = 600,
        metadata: dict | None = None,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = openrouter_chat(
            messages=messages,
            model=self.model,
            timeout=timeout,
            label=label,
        )
        choices = response.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "").strip()
