"""
Asset Generation (Phase 4a).

Generates all media assets needed for Remotion rendering:
- TTS audio (OpenRouter streaming)
- Subtitles (Whisper)
- Images (OpenRouter / Nano Banana 2)
- Scene timing from subtitle alignment
"""

import os
import sys
import json
import hashlib
import wave
import re

# Ensure project root is importable for src modules
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from citevideo.media import (
    build_cache_key,
    cache_audio_file,
    cache_image_file,
    cache_text_file,
    restore_cached_file,
)
from citevideo.backends.factory import (
    get_audio_backend,
    get_image_backend,
    get_transcription_backend,
)


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_tts(script: dict, assets_dir: str) -> str:
    """
    Generate TTS audio for the full script narration.

    Concatenates all scene narrations and generates a single WAV file
    using OpenRouter streaming TTS (pcm16 format).

    Returns path to the output WAV file.
    """
    from citevideo.config import get_openrouter_audio_model

    # Collect all narration text
    narration_parts = []
    for scene in script.get("scenes", []):
        narration = scene.get("narration", "").strip()
        if narration:
            narration_parts.append(narration)

    full_narration = "\n\n".join(narration_parts)
    print(f"  TTS: {len(full_narration)} chars, {len(full_narration.split())} words")

    model = get_openrouter_audio_model() or "openai/tts-1-hd"

    output_path = os.path.join(assets_dir, "narration.wav")
    cache_key = build_cache_key("tts", model, full_narration)
    if restore_cached_file(assets_dir, "audio", cache_key, ".wav", output_path):
        print(f"  TTS: cache hit ({cache_key[:10]})")
        return output_path

    try:
        backend = get_audio_backend()
        backend.synthesize(full_narration, output_path)
        with wave.open(output_path, "rb") as wf:
            duration = wf.getnframes() / max(wf.getframerate(), 1)
        print(f"  TTS: {duration:.1f}s WAV saved to {output_path}")
        cache_audio_file(assets_dir, cache_key, output_path)

    except Exception as e:
        print(f"  TTS FAILED: {e}")
        print(f"  Generating silent placeholder WAV so pipeline can continue...")
        # Generate a placeholder WAV (5 minutes of silence) so downstream steps work
        sample_rate = 24000
        duration_s = 300  # 5 minutes
        silent_frames = b"\x00\x00" * (sample_rate * duration_s)
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(silent_frames)
        print(f"  Placeholder WAV: {duration_s}s silence saved to {output_path}")

    return output_path


def generate_subtitles(wav_path: str, assets_dir: str) -> str:
    """
    Generate SRT subtitles from WAV using local Whisper.

    Returns path to the output SRT file.
    """
    srt_path = os.path.join(assets_dir, "narration.srt")
    cache_key = build_cache_key("transcript", _file_sha256(wav_path))
    if restore_cached_file(assets_dir, "transcripts", cache_key, ".srt", srt_path):
        print(f"  Subtitles: cache hit ({cache_key[:10]})")
        return srt_path

    try:
        backend = get_transcription_backend()
        backend.transcribe(wav_path, srt_path)
        segment_count = 0
        if os.path.exists(srt_path):
            with open(srt_path, "r", encoding="utf-8") as handle:
                segment_count = len(
                    [
                        block
                        for block in re.split(r"\n\n+", handle.read().strip())
                        if block.strip()
                    ]
                )
        print(f"  Subtitles: {segment_count} segments, saved to {srt_path}")
        cache_text_file(assets_dir, cache_key, srt_path)

    except Exception as e:
        print(f"  WARNING: Transcription unavailable, skipping subtitles: {e}")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("")

    return srt_path


def generate_images(script: dict, assets_dir: str, brand_colors: dict = None) -> dict:
    """
    Generate images for scenes that need them.

    Returns dict mapping scene_id -> image_path.
    """
    images_dir = os.path.join(assets_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    image_map = {}
    scenes_needing_images = []

    for scene in script.get("scenes", []):
        scene_type = scene.get("type", "")
        if scene_type in ("title", "talking_point", "image", "infographic"):
            scenes_needing_images.append(scene)

    print(f"  Images: generating for {len(scenes_needing_images)} scenes...")
    backend = get_image_backend()

    # Build color/style context
    style_note = ""
    if brand_colors:
        primary = brand_colors.get("primary", "#1a1a2e")
        accent = brand_colors.get("accent", "#e94560")
        style_note = (
            f"Use a clean, modern medical/science aesthetic. "
            f"Primary color: {primary}, accent: {accent}. "
            f"Dark background, professional look."
        )
    else:
        style_note = (
            "Use a clean, modern medical/science aesthetic. "
            "Dark navy/slate background, teal/cyan accents. "
            "Professional, trustworthy look."
        )

    for i, scene in enumerate(scenes_needing_images, 1):
        scene_id = scene.get("scene_id", f"scene_{i:03d}")
        visual_notes = scene.get("visual_notes", scene.get("heading", "health science"))

        prompt = (
            f"Create a clean, professional illustration for a health science video. "
            f"Scene: {visual_notes}. {style_note} "
            f"No text overlays. 16:9 aspect ratio. High quality, photorealistic or "
            f"clean vector illustration style."
        )
        cache_key = build_cache_key("image", "google/gemini-3.1-flash-image-preview", prompt)
        cached_png = os.path.join(images_dir, f"{scene_id}.png")
        cached_jpg = os.path.join(images_dir, f"{scene_id}.jpg")
        if restore_cached_file(assets_dir, "images", cache_key, ".png", cached_png):
            image_map[scene_id] = cached_png
            print(f"    [{i}/{len(scenes_needing_images)}] {scene_id}: cache hit")
            continue
        if restore_cached_file(assets_dir, "images", cache_key, ".jpg", cached_jpg):
            image_map[scene_id] = cached_jpg
            print(f"    [{i}/{len(scenes_needing_images)}] {scene_id}: cache hit")
            continue

        try:
            img_path = backend.generate(prompt, os.path.join(images_dir, f"{scene_id}.png"))
            image_map[scene_id] = img_path
            cache_image_file(assets_dir, cache_key, img_path, os.path.splitext(img_path)[1])
            print(f"    [{i}/{len(scenes_needing_images)}] {scene_id}: saved")

        except Exception as e:
            print(f"    [{i}/{len(scenes_needing_images)}] {scene_id}: FAILED - {e}")

    print(f"  Images: {len(image_map)}/{len(scenes_needing_images)} generated")
    return image_map


def compute_scene_timings(script: dict, srt_path: str) -> list:
    """
    Compute per-scene timing from the SRT file and narration text.

    Maps narration text to subtitle timestamps to determine
    when each scene starts and how long it lasts.

    Returns list of {scene_id, start_ms, duration_ms}.
    """
    scenes = script.get("scenes", [])

    # Parse SRT
    subtitles = []
    if os.path.exists(srt_path) and os.path.getsize(srt_path) > 0:
        with open(srt_path, "r") as f:
            content = f.read()

        blocks = re.split(r"\n\n+", content.strip())
        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:
                time_match = re.match(
                    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})",
                    lines[1],
                )
                if time_match:
                    g = [int(x) for x in time_match.groups()]
                    start_ms = g[0]*3600000 + g[1]*60000 + g[2]*1000 + g[3]
                    end_ms = g[4]*3600000 + g[5]*60000 + g[6]*1000 + g[7]
                    text = " ".join(lines[2:])
                    subtitles.append({"start_ms": start_ms, "end_ms": end_ms, "text": text})

    if not subtitles:
        # Fallback: estimate from word count
        print("  Timing: no subtitles available, estimating from word count")
        timings = []
        current_ms = 0
        for scene in scenes:
            words = len(scene.get("narration", "").split())
            duration_ms = max(3000, int(words / 2.5 * 1000))  # ~150 wpm
            timings.append({
                "scene_id": scene.get("scene_id"),
                "start_ms": current_ms,
                "duration_ms": duration_ms,
            })
            current_ms += duration_ms
        return timings

    # Match scenes to subtitle timings
    total_audio_ms = subtitles[-1]["end_ms"] if subtitles else 0
    total_words = sum(len(s.get("narration", "").split()) for s in scenes)

    timings = []
    current_ms = 0

    for scene in scenes:
        narration = scene.get("narration", "").strip()
        words = len(narration.split())

        if total_words > 0:
            proportion = words / total_words
            duration_ms = int(total_audio_ms * proportion)
        else:
            duration_ms = scene.get("duration_estimate_seconds", 10) * 1000

        duration_ms = max(2000, duration_ms)  # minimum 2 seconds

        timings.append({
            "scene_id": scene.get("scene_id"),
            "start_ms": current_ms,
            "duration_ms": duration_ms,
        })
        current_ms += duration_ms

    print(f"  Timing: {len(timings)} scenes, total {current_ms/1000:.1f}s")
    return timings


def generate_all_assets(run_dir: str) -> dict:
    """
    Generate all assets for the video.

    Args:
        run_dir: Run directory path

    Returns:
        Dict with paths to all generated assets
    """
    prod_dir = os.path.join(run_dir, "production")
    assets_dir = os.path.join(prod_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Load final script
    script_path = os.path.join(prod_dir, "script_v3.json")
    if not os.path.exists(script_path):
        script_path = os.path.join(prod_dir, "script_v2.json")
    if not os.path.exists(script_path):
        script_path = os.path.join(prod_dir, "script_v1.json")

    with open(script_path) as f:
        script = json.load(f)

    print(f"\n=== Phase 4a: Asset Generation ===")
    print(f"  Using script: {os.path.basename(script_path)}")

    # Load brand kit if available
    brand_colors = None
    brand_path = os.path.join(os.path.dirname(run_dir), "brand", "brand_kit.json")
    if os.path.exists(brand_path):
        with open(brand_path) as f:
            brand_kit = json.load(f)
            brand_colors = brand_kit.get("colors", {})

    # Generate TTS
    print("\n--- TTS ---")
    wav_path = generate_tts(script, assets_dir)

    # Generate subtitles
    print("\n--- Subtitles ---")
    srt_path = generate_subtitles(wav_path, assets_dir)

    # Generate images
    print("\n--- Images ---")
    image_map = generate_images(script, assets_dir, brand_colors)

    # Compute scene timings
    print("\n--- Scene Timing ---")
    timings = compute_scene_timings(script, srt_path)

    # Save asset manifest
    manifest = {
        "wav_path": wav_path,
        "srt_path": srt_path,
        "image_map": image_map,
        "timings": timings,
        "script_used": os.path.basename(script_path),
    }
    manifest_path = os.path.join(assets_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n  Asset manifest saved to {manifest_path}")
    return manifest
