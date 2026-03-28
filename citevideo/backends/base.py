"""
Abstract interfaces for pluggable knowledge and media backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TextTaskBackend(ABC):
    name: str = "text-backend"

    @abstractmethod
    def run(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        label: str = "",
        timeout: int = 180,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError


class ResearchBackend(TextTaskBackend):
    pass


class SynthesisBackend(TextTaskBackend):
    pass


class ReviewBackend(TextTaskBackend):
    pass
