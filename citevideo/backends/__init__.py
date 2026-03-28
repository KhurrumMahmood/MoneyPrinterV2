"""
Backend interfaces and default implementations for low-cost knowledge work.
"""

from .base import ResearchBackend, ReviewBackend, SynthesisBackend
from .claude_cli import ClaudeCliBackend
from .codex_cli import CodexCliBackend
from .factory import (
    get_audio_backend,
    get_image_backend,
    get_research_backend,
    get_review_backend,
    get_synthesis_backend,
    get_transcription_backend,
)
from .media import AudioBackend, ImageBackend, TranscriptionBackend
from .media_services import OpenRouterAudioBackend, OpenRouterImageBackend, WhisperLocalBackend
from .openrouter import OpenRouterBackend

__all__ = [
    "AudioBackend",
    "ClaudeCliBackend",
    "CodexCliBackend",
    "ImageBackend",
    "OpenRouterAudioBackend",
    "OpenRouterBackend",
    "OpenRouterImageBackend",
    "ResearchBackend",
    "ReviewBackend",
    "SynthesisBackend",
    "TranscriptionBackend",
    "WhisperLocalBackend",
    "get_audio_backend",
    "get_image_backend",
    "get_research_backend",
    "get_review_backend",
    "get_synthesis_backend",
    "get_transcription_backend",
]
