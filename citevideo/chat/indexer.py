"""
Export retrieval-grounded chat indices from package artifacts.
"""

from __future__ import annotations

import json
import os


def export_chat_index(run_dir: str) -> str:
    package_path = os.path.join(run_dir, "package", "chat_index.json")
    chat_dir = os.path.join(run_dir, "chat")
    os.makedirs(chat_dir, exist_ok=True)
    output_path = os.path.join(chat_dir, "chat_index.json")

    if os.path.exists(package_path):
        with open(package_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
    return output_path
