"""
Build a 3-min test video spec with per-scene TTS and audio-driven timing.

Each scene gets its own TTS audio file.
Scene duration = actual audio duration + padding.
This ensures perfect audio/video sync by construction.
"""

import os
import sys
import json
import wave
import base64
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from citevideo.config import get_openrouter_api_key, get_openrouter_base_url, get_openrouter_audio_model

API_KEY = get_openrouter_api_key()
BASE_URL = get_openrouter_base_url().rstrip("/")
TTS_MODEL = get_openrouter_audio_model() or "openai/tts-1-hd"

FPS = 30
SCENE_PADDING_MS = 1500  # 1.5s pause after each scene's audio
ASSETS_DIR = "remotion/public/assets/ben-azadi-stem-cells"
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")

# Selected scenes for 3-min test cut
SELECTED_SCENES = ["scene_001", "scene_002", "scene_004", "scene_006", "scene_008"]


def generate_scene_tts(scene_id: str, text: str) -> tuple[str, float]:
    """
    Generate TTS for a single scene.
    Returns (wav_path, duration_seconds).
    """
    output_path = os.path.join(AUDIO_DIR, f"{scene_id}.wav")

    # Clean narration text (remove stage directions in brackets)
    import re
    clean_text = re.sub(r'\[.*?\]', '', text).strip()
    clean_text = re.sub(r'\n\n+', '\n', clean_text).strip()

    print(f"  [{scene_id}] TTS: {len(clean_text)} chars...")

    try:
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": TTS_MODEL,
                "stream": True,
                "modalities": ["text", "audio"],
                "audio": {"voice": "alloy", "format": "pcm16"},
                "messages": [{"role": "user", "content":
                    f"Read this text aloud exactly as written, with natural pacing and expression:\n\n{clean_text}"}],
            },
            stream=True,
            timeout=300,
        )

        if response.status_code != 200:
            print(f"  [{scene_id}] TTS API error ({response.status_code}): {response.text[:200]}")
            return _make_silent_wav(output_path, estimate_duration(clean_text)), estimate_duration(clean_text)

        audio_b64_chunks = []
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                for choice in chunk.get("choices", []):
                    delta = choice.get("delta", {})
                    audio = delta.get("audio", {})
                    if audio.get("data"):
                        audio_b64_chunks.append(audio["data"])
            except json.JSONDecodeError:
                continue

        if not audio_b64_chunks:
            print(f"  [{scene_id}] No audio data, using silent placeholder")
            dur = estimate_duration(clean_text)
            return _make_silent_wav(output_path, dur), dur

        pcm_bytes = base64.b64decode("".join(audio_b64_chunks))
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm_bytes)

        duration = len(pcm_bytes) / (24000 * 2)
        print(f"  [{scene_id}] TTS: {duration:.1f}s saved")
        return output_path, duration

    except Exception as e:
        print(f"  [{scene_id}] TTS failed: {e}")
        dur = estimate_duration(clean_text)
        return _make_silent_wav(output_path, dur), dur


def estimate_duration(text: str) -> float:
    """Estimate speech duration from word count (~150 wpm)."""
    words = len(text.split())
    return max(3.0, words / 2.5)


def _make_silent_wav(path: str, duration_s: float) -> str:
    """Create a silent WAV file."""
    sample_rate = 24000
    frames = b"\x00\x00" * int(sample_rate * duration_s)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)
    return path


def build_spec():
    """Build the complete video spec with per-scene audio and real timing."""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # Load script
    script_path = "workspace/ben-azadi-stem-cells/production/script_v3.json"
    with open(script_path) as f:
        script = json.load(f)

    # Load image manifest if available
    image_manifest = {}
    manifest_path = os.path.join(IMAGES_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            image_manifest = json.load(f)

    # Filter to selected scenes
    selected = [s for s in script["scenes"] if s["scene_id"] in SELECTED_SCENES]

    print(f"\n=== Building Test Spec ({len(selected)} scenes) ===\n")

    # Evidence color mapping
    evidence_colors = {
        "strong": "#2DD4A0",
        "moderate": "#F5A623",
        "weak": "#E5484D",
        "mixed": "#F5A623",
        "none": "#666666",
    }

    scenes_spec = []
    total_duration_ms = 0

    for scene_data in selected:
        sid = scene_data["scene_id"]
        print(f"\n--- {sid}: {scene_data['heading']} ---")

        # Generate TTS for this scene
        wav_path, audio_duration = generate_scene_tts(sid, scene_data["narration"])

        # Scene duration = audio + padding
        scene_duration_ms = int(audio_duration * 1000) + SCENE_PADDING_MS
        scene_duration_frames = max(1, round((scene_duration_ms / 1000) * FPS))

        # Find image for this scene
        image_path = None
        for ext in ["png", "jpg", "jpeg"]:
            candidate = os.path.join(IMAGES_DIR, f"{sid}.{ext}")
            if os.path.exists(candidate):
                # Path relative to remotion/public/
                image_path = candidate.replace("remotion/public/", "")
                break

        # Build citations
        citations = []
        for cite in scene_data.get("citations_to_show", []):
            citations.append({
                "label": cite.get("label", ""),
                "detail": cite.get("detail", ""),
                "doi": cite.get("doi", ""),
                "timestamp": cite.get("timestamp", ""),
            })

        scene_spec = {
            "sceneId": sid,
            "type": scene_data["type"],
            "heading": scene_data["heading"],
            "narration": scene_data["narration"],
            "durationMs": scene_duration_ms,
            "durationFrames": scene_duration_frames,
            "mood": scene_data.get("mood", "neutral"),
            "evidenceStrength": scene_data.get("evidence_strength", "none"),
            "evidenceColor": evidence_colors.get(scene_data.get("evidence_strength", "none"), "#666"),
            "claimsReferenced": scene_data.get("claims_referenced", []),
            "visualNotes": scene_data.get("visual_notes", ""),
            "imagePath": image_path,
            "citations": citations,
            "audioPath": wav_path.replace("remotion/public/", "") if wav_path else None,
        }

        scenes_spec.append(scene_spec)
        total_duration_ms += scene_duration_ms

        print(f"  Audio: {audio_duration:.1f}s | Scene: {scene_duration_ms}ms ({scene_duration_frames}f)")
        if image_path:
            print(f"  Image: {image_path}")

    total_duration_frames = max(1, round((total_duration_ms / 1000) * FPS))

    # Build full spec
    spec = {
        "meta": {
            "runId": "ben-azadi-stem-cells-test",
            "title": script["title"],
            "fps": FPS,
            "width": 1920,
            "height": 1080,
            "totalDurationFrames": total_duration_frames,
            "totalDurationMs": total_duration_ms,
        },
        "brand": {
            "colors": {
                "primary": "#0A1628",
                "secondary": "#111B2E",
                "accent": "#2DD4A0",
                "text": "#F2F0ED",
                "textSecondary": "#8A9BB5",
                "success": "#2DD4A0",
                "warning": "#F5A623",
                "danger": "#E5484D",
            },
            "fonts": {
                "heading": "Inter, system-ui, sans-serif",
                "body": "Inter, system-ui, sans-serif",
            },
        },
        "audio": {
            "path": "",  # Per-scene audio, not global
            "srtPath": "",
        },
        "scenes": scenes_spec,
        "sourcesList": script.get("sources_list", []),
        "disclaimer": script.get("closing_disclaimer", ""),
    }

    # Write spec
    spec_path = "remotion/public/spec.json"
    with open(spec_path, "w") as f:
        json.dump(spec, f, indent=2)

    print(f"\n=== Spec Complete ===")
    print(f"  Scenes: {len(scenes_spec)}")
    print(f"  Duration: {total_duration_ms/1000:.1f}s ({total_duration_ms/60000:.1f} min)")
    print(f"  Frames: {total_duration_frames}")
    print(f"  Spec: {spec_path}")

    return spec_path


if __name__ == "__main__":
    build_spec()
