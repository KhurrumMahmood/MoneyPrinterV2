"""
Optional Codex CLI backend for local structured reviews or code-aware critique.
"""

from __future__ import annotations

import shutil
import subprocess

from citevideo.backends.base import ReviewBackend, SynthesisBackend


class CodexCliBackend(SynthesisBackend, ReviewBackend):
    name = "codex-cli"

    def __init__(self, executable: str = "codex") -> None:
        self.executable = executable

    def run(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        label: str = "",
        timeout: int = 180,
        metadata: dict | None = None,
    ) -> str:
        if not shutil.which(self.executable):
            raise RuntimeError(
                f"{self.executable} is not installed or not on PATH for CodexCliBackend."
            )

        payload = prompt if not system_prompt else f"{system_prompt}\n\n{prompt}"
        result = subprocess.run(
            [self.executable, "exec", payload],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Codex CLI failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        return result.stdout.strip()
