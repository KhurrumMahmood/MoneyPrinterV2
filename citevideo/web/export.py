"""
Export-first web payload generation.
"""

from __future__ import annotations

import json
import os
from typing import Any

from citevideo.web.hubs import export_topic_hubs


def export_web_payloads(run_dir: str) -> dict[str, str]:
    package_dir = os.path.join(run_dir, "package")
    web_dir = os.path.join(run_dir, "web")
    workspace_dir = os.path.dirname(run_dir)
    os.makedirs(web_dir, exist_ok=True)

    payloads = {}
    for name in ("web_dossier", "topic_hub_fragment"):
        src = os.path.join(package_dir, f"{name}.json")
        dst = os.path.join(web_dir, f"{name}.json")
        if os.path.exists(src):
            with open(src, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            with open(dst, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
            payloads[name] = dst

    hub_paths = export_topic_hubs(workspace_dir)
    payloads["topic_hubs_index"] = hub_paths["index"]

    fragment = None
    fragment_path = os.path.join(package_dir, "topic_hub_fragment.json")
    if os.path.exists(fragment_path):
        with open(fragment_path, "r", encoding="utf-8") as handle:
            fragment = json.load(handle)
    topic_slug = (fragment or {}).get("topic_slug")
    if topic_slug and topic_slug in hub_paths:
        dst = os.path.join(web_dir, "topic_hub.json")
        with open(hub_paths[topic_slug], "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        with open(dst, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        payloads["topic_hub"] = dst
    return payloads
