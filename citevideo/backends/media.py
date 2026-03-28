"""
Interfaces for paid-media operations that should remain swappable and cacheable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AudioBackend(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: str) -> str:
        raise NotImplementedError


class TranscriptionBackend(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str, output_path: str) -> str:
        raise NotImplementedError


class ImageBackend(ABC):
    @abstractmethod
    def generate(self, prompt: str, output_path: str) -> str:
        raise NotImplementedError
