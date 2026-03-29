"""
Review artifact helpers for CiteVideo.
"""

from __future__ import annotations

import os


def ensure_review_dirs(run_dir: str) -> dict[str, str]:
    root = os.path.join(run_dir, "review")
    paths = {
        "root": root,
        "script": os.path.join(root, "script"),
        "frames": os.path.join(root, "frames"),
        "frame_captures": os.path.join(root, "frames", "captures"),
        "preview": os.path.join(root, "preview"),
        "preview_frames": os.path.join(root, "preview", "frames"),
        "fixlists": os.path.join(root, "fixlists"),
    }
    for path in paths.values():
        os.makedirs(path, exist_ok=True)
    return paths

