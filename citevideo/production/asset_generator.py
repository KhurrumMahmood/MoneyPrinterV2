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
from citevideo.config import (
    get_audio_scene_padding_seconds,
    get_openrouter_audio_model,
    get_openrouter_audio_voice,
)


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_silence_wav(output_path: str, duration_seconds: float, sample_rate: int = 24000) -> float:
    duration_seconds = max(0.0, float(duration_seconds))
    silent_frames = b"\x00\x00" * int(sample_rate * duration_seconds)
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(silent_frames)
    return duration_seconds


def _append_silence_to_wav(output_path: str, duration_seconds: float) -> float:
    duration_seconds = max(0.0, float(duration_seconds))
    if duration_seconds <= 0:
        with wave.open(output_path, "rb") as wf:
            return wf.getnframes() / max(wf.getframerate(), 1)

    with wave.open(output_path, "rb") as wf:
        nchannels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    padding_frames = int(framerate * duration_seconds)
    padding_bytes = b"\x00" * (padding_frames * sampwidth * nchannels)

    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(nchannels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(framerate)
        wf.writeframes(frames + padding_bytes)

    return (len(frames) + len(padding_bytes)) / max(framerate * sampwidth * nchannels, 1)


def _wav_duration_seconds(path: str) -> float:
    with wave.open(path, "rb") as wf:
        return wf.getnframes() / max(wf.getframerate(), 1)


def _concat_wav_files(input_paths: list[str], output_path: str) -> float:
    if not input_paths:
        return _write_silence_wav(output_path, 1.0)

    frames_chunks: list[bytes] = []
    params: tuple[int, int, int] | None = None
    total_frames = 0

    for input_path in input_paths:
        with wave.open(input_path, "rb") as wf:
            current = (wf.getnchannels(), wf.getsampwidth(), wf.getframerate())
            if params is None:
                params = current
            elif current != params:
                raise RuntimeError(
                    f"Incompatible WAV parameters while concatenating audio: {input_path}"
                )
            frame_count = wf.getnframes()
            frames_chunks.append(wf.readframes(frame_count))
            total_frames += frame_count

    assert params is not None
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(params[0])
        wf.setsampwidth(params[1])
        wf.setframerate(params[2])
        wf.writeframes(b"".join(frames_chunks))

    return total_frames / max(params[2], 1)


def generate_tts(script: dict, assets_dir: str) -> dict:
    """
    Generate scene-by-scene TTS audio and stitch it into one narration track.

    Returns:
        {
            "wav_path": str,
            "scene_timings": list[dict],
            "scene_manifest_path": str,
        }
    """
    scenes = script.get("scenes", [])
    output_path = os.path.join(assets_dir, "narration.wav")
    scene_audio_dir = os.path.join(assets_dir, "scene-audio")
    os.makedirs(scene_audio_dir, exist_ok=True)

    model = get_openrouter_audio_model() or "openai/tts-1-hd"
    voice = get_openrouter_audio_voice()
    padding_seconds = get_audio_scene_padding_seconds()
    print(
        f"  TTS: {len(scenes)} scenes, model={model}, voice={voice}, "
        f"scene-padding={padding_seconds:.2f}s"
    )

    try:
        backend = get_audio_backend()
        scene_timings = []
        scene_manifest = []
        scene_audio_paths: list[str] = []
        current_ms = 0

        for scene in scenes:
            scene_id = scene.get("scene_id", f"scene_{len(scene_manifest) + 1:03d}")
            narration = scene.get("narration", "").strip()
            scene_output_path = os.path.join(scene_audio_dir, f"{scene_id}.wav")

            if narration:
                cache_key = build_cache_key(
                    "tts-scene-v2",
                    model,
                    voice,
                    f"{padding_seconds:.2f}",
                    narration,
                )
                cache_hit = restore_cached_file(
                    assets_dir, "audio", cache_key, ".wav", scene_output_path
                )
                if not cache_hit:
                    backend.synthesize(narration, scene_output_path)
                    _append_silence_to_wav(scene_output_path, padding_seconds)
                    cache_audio_file(assets_dir, cache_key, scene_output_path)
            else:
                silence_duration = max(
                    1.0, float(scene.get("duration_estimate_seconds", 3) or 3)
                )
                _write_silence_wav(scene_output_path, silence_duration)

            duration_seconds = _wav_duration_seconds(scene_output_path)
            duration_ms = int(duration_seconds * 1000)
            scene_timings.append(
                {
                    "scene_id": scene_id,
                    "start_ms": current_ms,
                    "duration_ms": duration_ms,
                }
            )
            scene_manifest.append(
                {
                    "scene_id": scene_id,
                    "audio_path": scene_output_path,
                    "duration_ms": duration_ms,
                    "has_narration": bool(narration),
                }
            )
            scene_audio_paths.append(scene_output_path)
            current_ms += duration_ms

        duration = _concat_wav_files(scene_audio_paths, output_path)
        scene_manifest_path = os.path.join(assets_dir, "scene_audio_manifest.json")
        with open(scene_manifest_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "model": model,
                    "voice": voice,
                    "scene_padding_seconds": padding_seconds,
                    "total_duration_ms": current_ms,
                    "scenes": scene_manifest,
                },
                handle,
                indent=2,
            )
        print(f"  TTS: stitched {len(scene_audio_paths)} scene clips into {duration:.1f}s WAV")

    except Exception as e:
        print(f"  TTS FAILED: {e}")
        print(f"  Generating silent placeholder WAV so pipeline can continue...")
        # Generate a placeholder WAV (5 minutes of silence) so downstream steps work
        duration_s = 300  # 5 minutes
        _write_silence_wav(output_path, duration_s)
        print(f"  Placeholder WAV: {duration_s}s silence saved to {output_path}")
        scene_timings = []
        current_ms = 0
        for scene in scenes:
            duration_ms = int(float(scene.get("duration_estimate_seconds", 10) or 10) * 1000)
            scene_timings.append(
                {
                    "scene_id": scene.get("scene_id"),
                    "start_ms": current_ms,
                    "duration_ms": duration_ms,
                }
            )
            current_ms += duration_ms
        scene_manifest_path = os.path.join(assets_dir, "scene_audio_manifest.json")
        with open(scene_manifest_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "model": model,
                    "voice": voice,
                    "scene_padding_seconds": padding_seconds,
                    "total_duration_ms": current_ms,
                    "scenes": [],
                },
                handle,
                indent=2,
            )

    return {
        "wav_path": output_path,
        "scene_timings": scene_timings,
        "scene_manifest_path": scene_manifest_path,
    }


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


def compute_scene_timings(script: dict, srt_path: str, precomputed_timings: list | None = None) -> list:
    """
    Compute per-scene timing from the SRT file and narration text.

    Maps narration text to subtitle timestamps to determine
    when each scene starts and how long it lasts.

    Returns list of {scene_id, start_ms, duration_ms}.
    """
    scenes = script.get("scenes", [])

    if precomputed_timings:
        total_ms = sum(int(item.get("duration_ms", 0)) for item in precomputed_timings)
        print(f"  Timing: using scene-audio timings ({len(precomputed_timings)} scenes, {total_ms/1000:.1f}s)")
        return precomputed_timings

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
    tts_bundle = generate_tts(script, assets_dir)
    wav_path = tts_bundle["wav_path"]

    # Generate subtitles
    print("\n--- Subtitles ---")
    srt_path = generate_subtitles(wav_path, assets_dir)

    # Generate images
    print("\n--- Images ---")
    image_map = generate_images(script, assets_dir, brand_colors)

    # Compute scene timings
    print("\n--- Scene Timing ---")
    timings = compute_scene_timings(script, srt_path, precomputed_timings=tts_bundle["scene_timings"])

    # Save asset manifest
    manifest = {
        "wav_path": wav_path,
        "srt_path": srt_path,
        "image_map": image_map,
        "timings": timings,
        "scene_audio_manifest_path": tts_bundle["scene_manifest_path"],
        "script_used": os.path.basename(script_path),
    }
    manifest_path = os.path.join(assets_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n  Asset manifest saved to {manifest_path}")
    return manifest
