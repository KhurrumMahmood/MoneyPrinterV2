"""
Generate TTS audio and images for the JSON video specification.

Usage:
    python src/agents/asset_agent.py --id <topic-id>

Reads spec.json, generates per-scene TTS WAVs and images,
then updates spec.json with correct durations and alignment.
"""

import os
import sys
import json
import base64
import wave
import struct
import re
import argparse
import requests
import time

# Load environment
from dotenv import load_dotenv
load_dotenv()

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_KEY = os.environ.get("OPENROUTER_API_KEY")
BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
AUDIO_MODEL = os.environ.get("OPENROUTER_AUDIO_MODEL", "openai/gpt-audio")
IMAGE_MODEL = os.environ.get("OPENROUTER_IMAGE_MODEL", "google/gemini-3.1-flash-image-preview")

FPS = 30


def generate_scene_tts(scene_id: str, narration: str, AUDIO_DIR: str) -> tuple[str, float]:
    """Generate TTS for a single scene. Returns (wav_path, duration_seconds)."""
    if not narration.strip():
        # Generate 3 seconds of silence for scenes with no narration
        wav_path = os.path.join(AUDIO_DIR, f"{scene_id}.wav")
        silence_frames = b"\x00\x00" * (24000 * 3)
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(silence_frames)
        return wav_path, 3.0

    wav_path = os.path.join(AUDIO_DIR, f"{scene_id}.wav")

    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": AUDIO_MODEL,
            "stream": True,
            "modalities": ["text", "audio"],
            "audio": {"voice": "alloy", "format": "pcm16"},
            "messages": [{"role": "user", "content":
                f"Read this text aloud exactly as written, with natural pacing and warm, conversational expression. "
                f"Speak as a knowledgeable friend explaining science — curious and engaging, not clinical:\n\n{narration}"}],
        },
        stream=True,
        timeout=120,
    )

    if response.status_code != 200:
        raise RuntimeError(f"TTS API error {response.status_code}: {response.text[:300]}")

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
        raise RuntimeError(f"TTS returned no audio data for {scene_id}")

    pcm_bytes = base64.b64decode("".join(audio_b64_chunks))

    # Add 0.75s padding of silence at the end for breathing room between scenes
    padding_frames = int(24000 * 0.75)
    padding_bytes = b"\x00\x00" * padding_frames
    pcm_bytes += padding_bytes

    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm_bytes)

    duration = len(pcm_bytes) / (24000 * 2)
    return wav_path, duration


def generate_scene_image(scene_id: str, visual_notes: str, IMAGES_DIR: str) -> str:
    """Generate a background image for a scene. Returns image path."""
    img_path = os.path.join(IMAGES_DIR, f"{scene_id}.png")
    
    # We rely heavily on the visual notes provided in the JSON spec.
    style_prompt = (
        "Warm, professional health science illustration. "
        "Soft lighting with teal and warm amber accents on a dark background. "
        "Clean, modern aesthetic suitable for a science video. "
        "No text, no words, no labels, no watermarks. "
        "16:9 aspect ratio. High quality."
    )

    prompt = f"{visual_notes}. {style_prompt}"

    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": IMAGE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
        },
        timeout=120,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Image API error {response.status_code}: {response.text[:300]}")

    data = response.json()
    for choice in data.get("choices", []):
        msg = choice.get("message", {})
        images = msg.get("images", [])
        for img in images:
            if isinstance(img, dict) and img.get("type") == "image_url":
                img_data = img.get("image_url", {}).get("url", "")
                if img_data.startswith("data:"):
                    b64 = img_data.split(",", 1)[1]
                    ext = "jpg" if "jpeg" in img_data or "jpg" in img_data else "png"
                    actual_path = os.path.join(IMAGES_DIR, f"{scene_id}.{ext}")
                    with open(actual_path, "wb") as f:
                        f.write(base64.b64decode(b64))
                    return actual_path
        
        parts = msg.get("content", [])
        if isinstance(parts, list):
            for part in parts:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    img_data = part.get("image_url", {}).get("url", "")
                    if img_data.startswith("data:"):
                        b64 = img_data.split(",", 1)[1]
                        with open(img_path, "wb") as f:
                            f.write(base64.b64decode(b64))
                        return img_path

    raise RuntimeError(f"No image found in response for {scene_id}")


def _normalize(word: str) -> str:
    """Strip punctuation and lowercase for fuzzy comparison."""
    return re.sub(r"[^a-z0-9']", "", word.lower())


def align_with_narration(narration: str, whisper_words: list[dict]) -> list[dict]:
    """Align Whisper timestamps with original narration text.
    Uses Whisper only for timing \u2014 words come from the original script.
    """
    orig_tokens = narration.split()
    orig_tokens = [t for t in orig_tokens if re.search(r"[a-zA-Z0-9]", t)]

    if not whisper_words:
        return [{"word": w, "startMs": i * 300, "endMs": (i + 1) * 300}
                for i, w in enumerate(orig_tokens)]

    aligned = []
    w_idx = 0 

    for o_idx, orig_word in enumerate(orig_tokens):
        orig_norm = _normalize(orig_word)

        if w_idx >= len(whisper_words):
            last_end = aligned[-1]["endMs"] if aligned else 0
            aligned.append({
                "word": orig_word,
                "startMs": last_end,
                "endMs": last_end + 300,
            })
            continue

        whisper_norm = _normalize(whisper_words[w_idx]["word"])

        if "-" in orig_word and whisper_norm != orig_norm:
            parts = orig_word.split("-")
            first_part_norm = _normalize(parts[0])
            if first_part_norm == whisper_norm or whisper_norm.startswith(first_part_norm):
                start_ms = whisper_words[w_idx]["startMs"]
                end_ms = whisper_words[w_idx]["endMs"]
                w_idx += 1
                while w_idx < len(whisper_words):
                    frag_norm = _normalize(whisper_words[w_idx]["word"])
                    end_ms = whisper_words[w_idx]["endMs"]
                    w_idx += 1
                    if any(_normalize(p) in frag_norm or frag_norm in _normalize(p)
                           for p in parts[1:]):
                        break
                aligned.append({"word": orig_word, "startMs": start_ms, "endMs": end_ms})
                continue

        best_match = w_idx
        for look in range(min(4, len(whisper_words) - w_idx)):
            candidate_norm = _normalize(whisper_words[w_idx + look]["word"])
            if candidate_norm == orig_norm or orig_norm in candidate_norm or candidate_norm in orig_norm:
                best_match = w_idx + look
                break

        aligned.append({
            "word": orig_word,
            "startMs": whisper_words[best_match]["startMs"],
            "endMs": whisper_words[best_match]["endMs"],
        })

        w_idx = best_match + 1

    return aligned


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True, help="ID of the project (e.g. glycine-poc)")
    parser.add_argument("--realign", action="store_true",
                        help="Force re-generation of word timings for all scenes")
    args = parser.parse_args()

    project_id = args.id
    SPEC_PATH = os.path.join(ROOT, "remotion", "public", project_id, "spec.json")
    AUDIO_DIR = os.path.join(ROOT, "remotion", "public", project_id, "audio")
    IMAGES_DIR = os.path.join(ROOT, "remotion", "public", project_id, "images")

    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)

    if not os.path.exists(SPEC_PATH):
        print(f"ERROR: Spec file not found at {SPEC_PATH}")
        sys.exit(1)

    with open(SPEC_PATH) as f:
        spec = json.load(f)

    scenes = spec["scenes"]
    total_duration_ms = 0

    print("=== Generating TTS Audio ===")
    for i, scene in enumerate(scenes):
        sid = scene["sceneId"]
        narration = scene.get("narration", "")
        wav_check = os.path.join(AUDIO_DIR, f"{sid}.wav")

        if os.path.exists(wav_check) and os.path.getsize(wav_check) > 1000:
            with wave.open(wav_check, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / rate
            scene["durationMs"] = int(duration * 1000)
            scene["durationFrames"] = int(duration * FPS)
            scene["audioPath"] = f"{project_id}/audio/{sid}.wav"
            total_duration_ms += scene["durationMs"]
            print(f"  [{i+1}/{len(scenes)}] {sid}: exists ({duration:.1f}s)")
            continue

        print(f"  [{i+1}/{len(scenes)}] {sid}: {len(narration)} chars...", end=" ", flush=True)
        try:
            wav_path, duration = generate_scene_tts(sid, narration, AUDIO_DIR)
            duration_ms = int(duration * 1000)
            duration_frames = int(duration * FPS)

            scene["durationMs"] = duration_ms
            scene["durationFrames"] = duration_frames
            scene["audioPath"] = f"{project_id}/audio/{sid}.wav"
            total_duration_ms += duration_ms

            print(f"{duration:.1f}s")
        except Exception as e:
            print(f"FAILED: {e}")

        time.sleep(0.5)

    print("\n=== Generating Background Images ===")
    for i, scene in enumerate(scenes):
        sid = scene["sceneId"]
        visual_notes = scene.get("visualNotes", "")

        if scene.get("type") == "source_list" or not visual_notes:
            print(f"  [{i+1}/{len(scenes)}] {sid}: skipped (no visual notes or source_list type)")
            continue

        existing_img = None
        for ext in ("png", "jpg", "jpeg"):
            candidate = os.path.join(IMAGES_DIR, f"{sid}.{ext}")
            if os.path.exists(candidate) and os.path.getsize(candidate) > 1000:
                existing_img = candidate
                break
        if existing_img:
            scene["imagePath"] = f"{project_id}/images/{os.path.basename(existing_img)}"
            print(f"  [{i+1}/{len(scenes)}] {sid}: exists ({os.path.basename(existing_img)})")
            continue

        print(f"  [{i+1}/{len(scenes)}] {sid}: generating...", end=" ", flush=True)
        try:
            img_path = generate_scene_image(sid, visual_notes, IMAGES_DIR)
            scene["imagePath"] = f"{project_id}/images/{os.path.basename(img_path)}"
            print("done")
        except Exception as e:
            print(f"FAILED: {e}")

        time.sleep(1)

    if args.realign:
        for scene in scenes:
            if "wordTimings" in scene:
                del scene["wordTimings"]
        print("\n  (--realign: cleared existing word timings)")

    print("\n=== Generating Word Timestamps ===")
    try:
        from faster_whisper import WhisperModel
        whisper_model = WhisperModel("base", device="cpu", compute_type="int8")

        for i, scene in enumerate(scenes):
            sid = scene["sceneId"]
            narration = scene.get("narration", "")
            if not narration.strip():
                print(f"  [{i+1}/{len(scenes)}] {sid}: skipped (no narration)")
                continue

            if scene.get("wordTimings") and len(scene["wordTimings"]) > 0:
                print(f"  [{i+1}/{len(scenes)}] {sid}: exists ({len(scene['wordTimings'])} words)")
                continue

            wav_path = os.path.join(AUDIO_DIR, f"{sid}.wav")
            if not os.path.exists(wav_path):
                print(f"  [{i+1}/{len(scenes)}] {sid}: skipped (no audio)")
                continue

            print(f"  [{i+1}/{len(scenes)}] {sid}: transcribing...", end=" ", flush=True)
            segments, _ = whisper_model.transcribe(wav_path, word_timestamps=True)

            whisper_words = []
            for segment in segments:
                if segment.words:
                    for w in segment.words:
                        whisper_words.append({
                            "word": w.word.strip(),
                            "startMs": int(w.start * 1000),
                            "endMs": int(w.end * 1000),
                        })

            aligned = align_with_narration(narration, whisper_words)
            scene["wordTimings"] = aligned
            print(f"{len(aligned)} words (aligned from {len(whisper_words)} whisper)")

    except ImportError:
        print("  WARNING: faster-whisper not available, skipping word timestamps")

    total_frames = sum(s.get("durationFrames", 0) for s in scenes)
    spec["meta"]["totalDurationMs"] = total_duration_ms
    spec["meta"]["totalDurationFrames"] = total_frames

    with open(SPEC_PATH, "w") as f:
        json.dump(spec, f, indent=2)

    print(f"\n=== Done ===")
    print(f"Total duration: {total_duration_ms/1000:.1f}s ({total_frames} frames)")
    print(f"Spec updated: {SPEC_PATH}")


if __name__ == "__main__":
    main()
