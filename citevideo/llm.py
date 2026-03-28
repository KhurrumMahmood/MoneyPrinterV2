"""
Claude CLI wrapper + OpenRouter API for CiteVideo.

Provides stateless LLM calls via Claude CLI subprocess and direct
OpenRouter HTTP calls for Perplexity research. Includes cost tracking
across all API calls.
"""

import os
import json
import time
import subprocess
from datetime import datetime
from citevideo.config import get_claude_model


# ---------------------------------------------------------------------------
# Cost Tracker
# ---------------------------------------------------------------------------

class CostTracker:
    """Accumulates API costs across all calls in a pipeline run."""

    def __init__(self):
        self.calls = []
        self.total_cost_usd = 0.0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def record(self, provider: str, model: str, prompt_tokens: int = 0,
               completion_tokens: int = 0, cost_usd: float = 0.0,
               latency_s: float = 0.0, label: str = "",
               cost_kind: str = "estimated"):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_usd": round(cost_usd, 6),
            "cost_kind": cost_kind,
            "latency_s": round(latency_s, 1),
            "label": label,
        }
        self.calls.append(entry)
        self.total_cost_usd += cost_usd
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens

    def summary(self) -> dict:
        by_provider = {}
        for c in self.calls:
            key = c["provider"]
            if key not in by_provider:
                by_provider[key] = {"calls": 0, "cost_usd": 0.0, "tokens": 0}
            by_provider[key]["calls"] += 1
            by_provider[key]["cost_usd"] += c["cost_usd"]
            by_provider[key]["tokens"] += c["total_tokens"]

        return {
            "total_calls": len(self.calls),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "by_provider": {k: {**v, "cost_usd": round(v["cost_usd"], 4)}
                           for k, v in by_provider.items()},
            "calls": self.calls,
        }

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.summary(), f, indent=2)

    def print_summary(self):
        s = self.summary()
        print(f"\n{'='*50}")
        print(f"  API Cost Summary")
        print(f"{'='*50}")
        print(f"  Total calls: {s['total_calls']}")
        print(f"  Total cost:  ${s['total_cost_usd']:.4f}")
        print(f"  Total tokens: {s['total_prompt_tokens'] + s['total_completion_tokens']:,}")
        for provider, data in s["by_provider"].items():
            print(f"  {provider}: {data['calls']} calls, ${data['cost_usd']:.4f}, "
                  f"{data['tokens']:,} tokens")
        print(f"{'='*50}")


# Global tracker instance — shared across all calls in a pipeline run
_tracker = CostTracker()


def get_tracker() -> CostTracker:
    return _tracker


def reset_tracker():
    global _tracker
    _tracker = CostTracker()


# ---------------------------------------------------------------------------
# Claude CLI
# ---------------------------------------------------------------------------

# Approximate Claude pricing per 1M tokens (Sonnet via CLI)
_CLAUDE_PRICING = {
    "sonnet": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "opus": {"input": 15.0, "output": 75.0},
    "haiku": {"input": 0.25, "output": 1.25},
}


def _estimate_claude_cost(model: str, prompt_chars: int, response_chars: int) -> tuple:
    """Estimate tokens and cost for a Claude CLI call."""
    prompt_tokens = int(prompt_chars / 4)  # ~4 chars per token
    completion_tokens = int(response_chars / 4)
    pricing = _CLAUDE_PRICING.get(model, _CLAUDE_PRICING.get("sonnet"))
    cost = (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1_000_000
    return prompt_tokens, completion_tokens, cost


def claude(prompt: str, system_prompt: str = None, model: str = None,
           timeout: int = 180, label: str = "", max_retries: int = 5) -> str:
    """
    Single stateless Claude CLI call with cost tracking and retry on overload.

    Args:
        prompt: The user prompt text
        system_prompt: Optional system prompt for persona/role
        model: Optional model override (defaults to config)
        timeout: Subprocess timeout in seconds
        label: Optional label for cost tracking
        max_retries: Max retries on transient errors (529 overloaded)

    Returns:
        The model's text response, stripped of whitespace
    """
    model = model or get_claude_model()
    cmd = ["claude", "-p", "--model", model, "--tools", ""]

    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])

    last_error = None
    for attempt in range(max_retries):
        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            wait = min(30, 10 * (attempt + 1))
            last_error = f"Timed out after {timeout}s"
            print(f"    Timeout (attempt {attempt + 1}/{max_retries}), "
                  f"retrying in {wait}s...")
            time.sleep(wait)
            continue
        elapsed = time.time() - start

        if result.returncode == 0:
            break

        stderr = result.stderr.strip()
        # Retry on overloaded (529) or transient errors
        if "overloaded" in stderr.lower() or "529" in stderr or "rate" in stderr.lower():
            wait = min(30, 5 * (attempt + 1))
            last_error = stderr
            print(f"    API overloaded (attempt {attempt + 1}/{max_retries}), "
                  f"retrying in {wait}s...")
            time.sleep(wait)
            continue

        raise RuntimeError(
            f"Claude CLI failed (exit {result.returncode}): {stderr}"
        )
    else:
        raise RuntimeError(
            f"Claude CLI failed after {max_retries} retries: {last_error}"
        )

    response_text = result.stdout.strip()

    # Track cost
    total_input = len(prompt) + len(system_prompt or "")
    pt, ct, cost = _estimate_claude_cost(model, total_input, len(response_text))
    _tracker.record(
        provider="claude-cli",
        model=model,
        prompt_tokens=pt,
        completion_tokens=ct,
        cost_usd=cost,
        cost_kind="estimated",
        latency_s=elapsed,
        label=label,
    )

    return response_text


# ---------------------------------------------------------------------------
# OpenRouter API
# ---------------------------------------------------------------------------

def openrouter_chat(
    messages: list,
    model: str,
    timeout: int = 600,
    extra_json: dict = None,
    label: str = "",
) -> dict:
    """
    Direct OpenRouter chat completions call with cost tracking.

    Args:
        messages: List of {"role": ..., "content": ...} dicts
        model: OpenRouter model ID
        timeout: Request timeout in seconds
        extra_json: Additional fields to merge into the request body
        label: Optional label for cost tracking

    Returns:
        The parsed JSON response body
    """
    import requests
    from citevideo.config import get_openrouter_api_key, get_openrouter_base_url

    api_key = get_openrouter_api_key()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    base_url = get_openrouter_base_url().rstrip("/")

    body = {
        "model": model,
        "messages": messages,
    }
    if extra_json:
        body.update(extra_json)

    start = time.time()
    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=timeout,
    )
    elapsed = time.time() - start
    response.raise_for_status()
    data = response.json()

    # Extract usage info from OpenRouter response
    usage = data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)

    # OpenRouter often includes cost in the response or we can estimate
    # Perplexity sonar-deep-research: ~$2/1M input, ~$8/1M output (approximate)
    cost = 0.0
    if "perplexity" in model:
        cost = (prompt_tokens * 2.0 + completion_tokens * 8.0) / 1_000_000
    elif "google" in model:
        cost = (prompt_tokens * 0.1 + completion_tokens * 0.4) / 1_000_000
    else:
        cost = (prompt_tokens * 1.0 + completion_tokens * 2.0) / 1_000_000

    _tracker.record(
        provider="openrouter",
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost,
        cost_kind="estimated",
        latency_s=elapsed,
        label=label,
    )

    return data
