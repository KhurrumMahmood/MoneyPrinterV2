"""Generate scene images for the 3-min test cut using OpenRouter (Gemini image gen)."""

import os
import sys
import json
import base64
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from citevideo.config import get_openrouter_api_key, get_openrouter_base_url

API_KEY = get_openrouter_api_key()
BASE_URL = get_openrouter_base_url().rstrip("/")
MODEL = "google/gemini-3.1-flash-image-preview"
OUTPUT_DIR = "remotion/public/assets/ben-azadi-stem-cells/images"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Scene image prompts - cinematic, 16:9, health/science aesthetic
PROMPTS = {
    "scene_001": (
        "Cinematic close-up of a glass morning health drink with amber-golden liquid on a dark navy "
        "clinical surface. Soft volumetric lighting from the left. A translucent research paper or "
        "citation card hovers dissolving into particles above the glass. Cool blue-teal accent light "
        "reflects off the glass. Dark moody background. 16:9 aspect ratio. Photorealistic. "
        "No text, no words, no letters."
    ),
    "scene_002": (
        "Abstract scientific visualization of human cells performing autophagy. Bioluminescent cyan "
        "and teal glowing cells on a deep navy-black background. One cell shows internal recycling "
        "process with glowing organelles being broken down. Ethereal, luminous quality. Microscopy "
        "aesthetic with artistic interpretation. 16:9 aspect ratio. No text, no words, no letters."
    ),
    "scene_004": (
        "Split composition: left side shows a jar of golden honey with a dramatic spotlight, right "
        "side shows an abstract DNA double helix dissolving into question marks. Dark background with "
        "amber and red accent lighting. Clinical, investigative mood. The honey glows warmly while "
        "the right side is cooler blue-teal. 16:9 aspect ratio. Photorealistic. "
        "No text, no words, no letters."
    ),
    "scene_006": (
        "Dark dramatic still life of prescription medication bottles and capsules on a black surface "
        "with a single harsh amber warning light from above. Black pepper scattered among the pills. "
        "Moody, cautionary atmosphere. Shallow depth of field. Film noir lighting. "
        "16:9 aspect ratio. Photorealistic. No text, no words, no letters."
    ),
    "scene_008": (
        "Warm golden-hour macro photograph of healthy human cells, abstract and luminous. Soft "
        "golden and cyan bioluminescent glow suggesting vitality and renewal. Hopeful, uplifting "
        "mood. Clean, minimal composition with one bright cell cluster in center. "
        "Dark background transitioning to warm gold. 16:9 aspect ratio. "
        "No text, no words, no letters."
    ),
}


def generate_image(scene_id: str, prompt: str) -> str | None:
    """Generate a single image via OpenRouter."""
    print(f"\n  [{scene_id}] Generating...")

    try:
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "modalities": ["image", "text"],
            },
            timeout=120,
        )

        if response.status_code != 200:
            print(f"  [{scene_id}] API error {response.status_code}: {response.text[:200]}")
            # Try fallback model
            return generate_image_fallback(scene_id, prompt)

        data = response.json()
        choices = data.get("choices", [])

        for choice in choices:
            parts = choice.get("message", {}).get("content", [])
            if isinstance(parts, list):
                for part in parts:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        img_data = part.get("image_url", {}).get("url", "")
                        if img_data.startswith("data:"):
                            b64 = img_data.split(",", 1)[1]
                            ext = "jpg" if "jpeg" in img_data or "jpg" in img_data else "png"
                            img_path = os.path.join(OUTPUT_DIR, f"{scene_id}.{ext}")
                            with open(img_path, "wb") as f:
                                f.write(base64.b64decode(b64))
                            print(f"  [{scene_id}] Saved: {img_path}")
                            return img_path

            # Check message.images format
            images = choice.get("message", {}).get("images", [])
            for img in images:
                url = img.get("image_url", {}).get("url", "")
                if url.startswith("data:image"):
                    b64 = url.split(",", 1)[1]
                    img_path = os.path.join(OUTPUT_DIR, f"{scene_id}.png")
                    with open(img_path, "wb") as f:
                        f.write(base64.b64decode(b64))
                    print(f"  [{scene_id}] Saved: {img_path}")
                    return img_path

        print(f"  [{scene_id}] No image in response, trying fallback...")
        return generate_image_fallback(scene_id, prompt)

    except Exception as e:
        print(f"  [{scene_id}] FAILED: {e}")
        return generate_image_fallback(scene_id, prompt)


def generate_image_fallback(scene_id: str, prompt: str) -> str | None:
    """Try alternative model names."""
    fallback_models = [
        "google/gemini-2.5-flash-image",
        "google/gemini-3-pro-image-preview",
    ]

    for model in fallback_models:
        print(f"  [{scene_id}] Trying fallback: {model}")
        try:
            response = requests.post(
                f"{BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "modalities": ["image", "text"],
                },
                timeout=120,
            )

            if response.status_code != 200:
                print(f"  [{scene_id}] {model} error: {response.status_code}")
                continue

            data = response.json()
            for choice in data.get("choices", []):
                parts = choice.get("message", {}).get("content", [])
                if isinstance(parts, list):
                    for part in parts:
                        if isinstance(part, dict) and part.get("type") == "image_url":
                            img_data = part.get("image_url", {}).get("url", "")
                            if img_data.startswith("data:"):
                                b64 = img_data.split(",", 1)[1]
                                ext = "jpg" if "jpeg" in img_data else "png"
                                img_path = os.path.join(OUTPUT_DIR, f"{scene_id}.{ext}")
                                with open(img_path, "wb") as f:
                                    f.write(base64.b64decode(b64))
                                print(f"  [{scene_id}] Saved via {model}: {img_path}")
                                return img_path

        except Exception as e:
            print(f"  [{scene_id}] {model} failed: {e}")
            continue

    print(f"  [{scene_id}] All models failed")
    return None


if __name__ == "__main__":
    print("=== Generating Scene Images ===")
    results = {}
    for scene_id, prompt in PROMPTS.items():
        path = generate_image(scene_id, prompt)
        if path:
            results[scene_id] = path

    print(f"\n=== Results: {len(results)}/{len(PROMPTS)} images generated ===")
    for sid, path in results.items():
        print(f"  {sid}: {path}")

    # Save manifest
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nManifest saved to {manifest_path}")
