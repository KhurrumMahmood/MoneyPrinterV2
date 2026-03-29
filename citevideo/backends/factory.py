"""
Backend selection helpers with low-cost defaults.
"""

from __future__ import annotations

from citevideo.backends.claude_cli import ClaudeCliBackend
from citevideo.backends.codex_cli import CodexCliBackend
from citevideo.backends.media_services import (
    DisabledImageBackend,
    MacOSSayAudioBackend,
    OpenRouterAudioBackend,
    OpenRouterImageBackend,
    WhisperLocalBackend,
)
from citevideo.backends.openrouter import OpenRouterBackend
from citevideo.config import (
    allow_openrouter_research,
    get_audio_backend_name,
    get_codex_cli_command,
    get_image_backend_name,
    get_research_backend_name,
    get_review_backend_name,
    get_synthesis_backend_name,
    get_transcription_backend_name,
)


def _resolve_backend(name: str):
    normalized = (name or "claude-cli").strip().lower()
    if normalized == "claude-cli":
        return ClaudeCliBackend()
    if normalized == "codex-cli":
        return CodexCliBackend(executable=get_codex_cli_command())
    if normalized == "openrouter":
        if not allow_openrouter_research():
            raise RuntimeError(
                "OpenRouter research backend requested, but CITEVIDEO_ENABLE_OPENROUTER_RESEARCH is not enabled."
            )
        return OpenRouterBackend()
    raise ValueError(f"Unknown CiteVideo backend: {name}")


def get_research_backend():
    return _resolve_backend(get_research_backend_name())


def get_synthesis_backend():
    return _resolve_backend(get_synthesis_backend_name())


def get_review_backend():
    return _resolve_backend(get_review_backend_name())


def _resolve_audio_backend(name: str):
    normalized = (name or "openrouter-audio").strip().lower()
    if normalized == "openrouter-audio":
        return OpenRouterAudioBackend()
    if normalized in {"macos-say", "say"}:
        return MacOSSayAudioBackend()
    raise ValueError(f"Unknown CiteVideo audio backend: {name}")


def _resolve_transcription_backend(name: str):
    normalized = (name or "whisper-local").strip().lower()
    if normalized == "whisper-local":
        return WhisperLocalBackend()
    raise ValueError(f"Unknown CiteVideo transcription backend: {name}")


def _resolve_image_backend(name: str):
    normalized = (name or "openrouter-image").strip().lower()
    if normalized == "openrouter-image":
        return OpenRouterImageBackend()
    if normalized in {"disabled", "none"}:
        return DisabledImageBackend()
    raise ValueError(f"Unknown CiteVideo image backend: {name}")


def get_audio_backend():
    return _resolve_audio_backend(get_audio_backend_name())


def get_transcription_backend():
    return _resolve_transcription_backend(get_transcription_backend_name())


def get_image_backend():
    return _resolve_image_backend(get_image_backend_name())
