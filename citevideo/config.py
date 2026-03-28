"""
CiteVideo configuration.

Wraps the existing MoneyPrinterV2 config (src/config.py) and adds
CiteVideo-specific settings. All OpenRouter getters are re-exported
so citevideo modules don't need to import from src/.
"""

import os
import sys
import json

# Ensure src/ is importable
_src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency in lightweight setups
    def load_dotenv(*_args, **_kwargs):
        return False

# Load .env from project root
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_root, ".env"))

ROOT_DIR = _root
WORKSPACE_DIR = os.path.join(ROOT_DIR, "workspace")


# --- Re-exported from src/config.py ---

def get_openrouter_api_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "")

def get_openrouter_base_url() -> str:
    return os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

def get_openrouter_image_model() -> str:
    return os.environ.get("OPENROUTER_IMAGE_MODEL", "")

def get_openrouter_audio_model() -> str:
    return os.environ.get("OPENROUTER_AUDIO_MODEL", "")

def get_openrouter_research_model() -> str:
    return os.environ.get("OPENROUTER_RESEARCH_MODEL", "perplexity/sonar-deep-research")


# --- CiteVideo-specific config ---

def get_claude_model() -> str:
    """Claude model for CLI subprocess calls."""
    config_path = os.path.join(ROOT_DIR, "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f).get("claude_model", "sonnet")
    return "sonnet"

def get_roundtable_rounds() -> int:
    """Number of discussion rounds in the multi-agent roundtable."""
    return int(os.environ.get("CITEVIDEO_ROUNDTABLE_ROUNDS", "12"))


def get_research_backend_name() -> str:
    """Default research backend for knowledge tasks."""
    return os.environ.get("CITEVIDEO_RESEARCH_BACKEND", "claude-cli").strip().lower()


def get_synthesis_backend_name() -> str:
    """Default synthesis backend for planning and writing tasks."""
    return os.environ.get("CITEVIDEO_SYNTHESIS_BACKEND", "claude-cli").strip().lower()


def get_review_backend_name() -> str:
    """Default review backend for audits or critiques."""
    return os.environ.get("CITEVIDEO_REVIEW_BACKEND", "claude-cli").strip().lower()


def get_audio_backend_name() -> str:
    """Default audio generation backend for paid media."""
    return os.environ.get("CITEVIDEO_AUDIO_BACKEND", "openrouter-audio").strip().lower()


def get_transcription_backend_name() -> str:
    """Default transcription backend for paid media."""
    return os.environ.get("CITEVIDEO_TRANSCRIPTION_BACKEND", "whisper-local").strip().lower()


def get_image_backend_name() -> str:
    """Default image generation backend for paid media."""
    return os.environ.get("CITEVIDEO_IMAGE_BACKEND", "openrouter-image").strip().lower()


def allow_openrouter_research() -> bool:
    """Whether paid OpenRouter research calls are allowed."""
    return os.environ.get("CITEVIDEO_ENABLE_OPENROUTER_RESEARCH", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def get_codex_cli_command() -> str:
    """Executable used for optional Codex CLI backend integration."""
    return os.environ.get("CITEVIDEO_CODEX_COMMAND", "codex").strip() or "codex"

def get_workspace_dir() -> str:
    return WORKSPACE_DIR

def get_brand_dir() -> str:
    return os.path.join(WORKSPACE_DIR, "brand")

def get_run_dir(run_id: str) -> str:
    return os.path.join(WORKSPACE_DIR, run_id)

def ensure_run_dirs(run_id: str) -> str:
    """Create the full workspace directory tree for a run. Returns run_dir."""
    run_dir = get_run_dir(run_id)
    for sub in [
        "",
        "package",
        "package/audits",
        "roundtable",
        "production",
        "production/assets",
        "review",
        "output",
        "web",
        "chat",
    ]:
        os.makedirs(os.path.join(run_dir, sub), exist_ok=True)
    return run_dir
