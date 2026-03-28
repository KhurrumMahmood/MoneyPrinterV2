"""
Claude CLI backend wrappers for research, synthesis, and review work.
"""

from __future__ import annotations

from citevideo.backends.base import ResearchBackend, ReviewBackend, SynthesisBackend
from citevideo.llm import claude


class ClaudeCliBackend(ResearchBackend, SynthesisBackend, ReviewBackend):
    name = "claude-cli"

    def run(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        label: str = "",
        timeout: int = 180,
        metadata: dict | None = None,
    ) -> str:
        return claude(
            prompt=prompt,
            system_prompt=system_prompt,
            timeout=timeout,
            label=label,
        )
