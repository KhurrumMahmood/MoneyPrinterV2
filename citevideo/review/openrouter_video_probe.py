"""
Low-cost OpenRouter video review probe for CiteVideo.

Uses a free video-understanding model to critique a short local clip.
This is intended for hook / preview QA, not publication-time review.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from datetime import datetime, timezone

from citevideo.config import get_openrouter_api_key
from citevideo.llm import openrouter_chat
from citevideo.review.models import ensure_review_dirs


DEFAULT_MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"

DEFAULT_PROMPT = """You are reviewing a short-form health video prototype.

Return valid JSON only with this schema:
{
  "model_role": "video_reviewer",
  "overall_verdict": "pass|revise|block",
  "scores": {
    "hook": 0,
    "clarity": 0,
    "trust": 0,
    "visual_quality": 0,
    "craftedness": 0
  },
  "strengths": ["..."],
  "problems": [
    {
      "severity": "critical|major|minor",
      "title": "...",
      "why_it_matters": "...",
      "suggested_fix": "..."
    }
  ],
  "comparison_to_baseline": {
    "feels_more_alive_than_output_v5": false,
    "explanation": "..."
  },
  "one_sentence_summary": "..."
}

Review criteria:
- Does the first 3 seconds visually hook?
- Does it feel like a crafted short rather than a slide deck?
- Are the visuals concrete and image-led, or still too UI-like?
- Does the evidence framing build trust without killing momentum?
- Be direct and specific.
"""


def _encode_video(path: str) -> str:
    with open(path, "rb") as handle:
        payload = base64.b64encode(handle.read()).decode("ascii")
    return f"data:video/mp4;base64,{payload}"


def run_probe(video_path: str, prompt: str, model: str) -> dict:
    if not get_openrouter_api_key():
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    if not os.path.exists(video_path):
        raise FileNotFoundError(video_path)

    video_data_url = _encode_video(video_path)
    response = openrouter_chat(
        model=model,
        timeout=240,
        label="video-probe",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "video_url",
                        "videoUrl": {
                            "url": video_data_url,
                        },
                    },
                ],
            }
        ],
        extra_json={
            "temperature": 0.1,
        },
    )
    return response


def _extract_text(response: dict) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")).strip())
        return "\n".join(part for part in parts if part).strip()
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe a local video with a free OpenRouter video model.")
    parser.add_argument("--run-dir", required=True, help="CiteVideo run directory")
    parser.add_argument("--video", required=True, help="Local MP4 clip to review")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model ID")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Review prompt")
    parser.add_argument("--output-name", default="openrouter-video-probe", help="Output file prefix")
    args = parser.parse_args()

    review_dirs = ensure_review_dirs(args.run_dir)
    response = run_probe(args.video, args.prompt, args.model)
    response_text = _extract_text(response)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_path = os.path.join(review_dirs["preview"], f"{args.output_name}-{timestamp}-raw.json")
    text_path = os.path.join(review_dirs["preview"], f"{args.output_name}-{timestamp}.txt")

    with open(raw_path, "w", encoding="utf-8") as handle:
        json.dump(response, handle, indent=2)

    with open(text_path, "w", encoding="utf-8") as handle:
        handle.write(response_text)
        handle.write("\n")

    print(f"model={args.model}")
    print(f"raw={raw_path}")
    print(f"text={text_path}")
    if response_text:
        print("")
        print(response_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
