"""
Generate real scene backgrounds for the CiteVideo pilot run.

This is intentionally opinionated and tuned for early proof-of-concept
quality work: a few stronger hero images are more valuable than many
generic ones.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Iterable

from citevideo.backends.factory import get_image_backend
from citevideo.media import build_cache_key, cache_image_file, restore_cached_file
from citevideo.production.spec_builder import build_spec


PROMPT_OVERRIDES: dict[str, str] = {
    "scene_001": """
Use case: photorealistic-natural
Asset type: vertical short-form health video hook background
Primary request: cinematic editorial breakfast experiment image showing two clear before-and-after meal states
Scene/backdrop: dark navy stone kitchen table, premium moody health-documentary aesthetic
Subject: left side plain bagel and a small glass of orange juice; right side the same bagel and orange juice with peanut butter added as the single visible swap
Style/medium: high-end editorial food photography, photorealistic
Composition/framing: 9:16 portrait, top-down view, meals anchored in the lower half, clean negative space in the upper half for headline text, clear visual separation between left and right
Lighting/mood: dramatic soft directional morning light, cinematic shadows, trustworthy and premium
Color palette: deep navy, cream, warm bread tones, subtle teal health-tech accents
Materials/textures: glossy glass, toasted bagel texture, creamy peanut butter, matte stone surface
Constraints: no text, no labels, no charts, no split-screen graphics, no watermark
Avoid: extra foods, cluttered props, hands, cutlery overload, collage look, infographic look
""".strip(),
    "scene_002": """
Use case: photorealistic-natural
Asset type: vertical short-form health video teaching background
Primary request: a refined overhead breakfast-prep scene that makes “pair, order, choose” feel practical and premium
Scene/backdrop: dark kitchen counter with one plated breakfast and neatly arranged supporting ingredients
Subject: a plate with vegetables, intact grain toast, avocado, egg, and a small bowl of berries arranged with visual order and clarity
Style/medium: editorial health-food photography, photorealistic
Composition/framing: 9:16 portrait, top-down view, strongest food composition in the middle-to-lower half, generous negative space for text on the upper left
Lighting/mood: warm morning light with soft contrast, calm and confident
Color palette: deep slate background, natural greens, warm grain tones, subtle gold highlights
Materials/textures: ceramic plate, fresh vegetable texture, toasted grain detail, realistic food styling
Constraints: no text, no labels, no icons, no watermark
Avoid: messy table, too many ingredients, stock-photo vibe, bright white background
""".strip(),
    "scene_003": """
Use case: photorealistic-natural
Asset type: vertical short-form health video explanatory background
Primary request: overhead breakfast scene that visually communicates protein pairing as the practical move
Scene/backdrop: dark stone breakfast table with one carb-heavy meal being upgraded by protein add-ins
Subject: a central breakfast plate with toast or bagel plus egg and tofu, with a protein shake and chicken side dish positioned nearby as optional pairings
Style/medium: cinematic editorial food photography, photorealistic
Composition/framing: 9:16 portrait, top-down with the main plate centered in the lower-middle frame and surrounding add-ins arranged cleanly around it, room for headline in upper left
Lighting/mood: dramatic but appetizing, premium health documentary feel
Color palette: navy, charcoal, warm whites, muted greens, subtle teal accents
Materials/textures: ceramic plate, creamy egg yolk, tofu texture, realistic glass shake, crisp shadows
Constraints: no text, no labels, no infographic overlays, no watermark
Avoid: clutter, too many props, restaurant plating, cartoon styling
""".strip(),
    "scene_004": """
Use case: photorealistic-natural
Asset type: vertical short-form health video explanatory background
Primary request: elegant overhead composition showing fat and fiber additions that make a carb-heavy meal gentler
Scene/backdrop: dark navy kitchen surface with a central carb meal and supportive additions around it
Subject: avocado, nuts, vegetables, and a glass of fiber drink placed around a simple grain-based meal
Style/medium: editorial food photography, photorealistic
Composition/framing: 9:16 portrait, top-down with ingredients arranged as a clean radial composition in the lower two-thirds, negative space up top for title
Lighting/mood: cinematic, grounded, practical
Color palette: deep navy, avocado greens, warm grain browns, subtle amber and teal accents
Materials/textures: fresh produce detail, matte nuts, glass reflections, realistic food styling
Constraints: no text, no charts, no labels, no watermark
Avoid: sterile stock image look, too many bowls, bright kitchen background
""".strip(),
}


def _load_manifest(run_dir: str) -> tuple[str, dict]:
    manifest_path = os.path.join(run_dir, "production", "assets", "manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as handle:
        return manifest_path, json.load(handle)


def _save_manifest(manifest_path: str, manifest: dict) -> None:
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)


def _iter_scene_ids(requested: Iterable[str] | None) -> list[str]:
    if requested:
        scene_ids = [scene_id.strip() for scene_id in requested if scene_id.strip()]
        return scene_ids or list(PROMPT_OVERRIDES)
    return list(PROMPT_OVERRIDES)


def generate_images_for_run(run_dir: str, scene_ids: Iterable[str] | None = None) -> dict[str, str]:
    manifest_path, manifest = _load_manifest(run_dir)
    image_map = dict(manifest.get("image_map", {}))
    backend = get_image_backend()
    assets_dir = os.path.join(run_dir, "production", "assets")
    images_dir = os.path.join(assets_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    selected = _iter_scene_ids(scene_ids)
    for scene_id in selected:
        prompt = PROMPT_OVERRIDES.get(scene_id)
        if not prompt:
            continue

        base_output = os.path.join(images_dir, f"{scene_id}.png")
        cache_key = build_cache_key("pilot-image", "google/gemini-3.1-flash-image-preview", prompt)

        png_candidate = os.path.splitext(base_output)[0] + ".png"
        jpg_candidate = os.path.splitext(base_output)[0] + ".jpg"
        if restore_cached_file(assets_dir, "images", cache_key, ".png", png_candidate):
            image_map[scene_id] = png_candidate
            print(f"[images] {scene_id}: cache hit (png)")
            continue
        if restore_cached_file(assets_dir, "images", cache_key, ".jpg", jpg_candidate):
            image_map[scene_id] = jpg_candidate
            print(f"[images] {scene_id}: cache hit (jpg)")
            continue

        print(f"[images] {scene_id}: generating...")
        generated_path = backend.generate(prompt, base_output)
        image_map[scene_id] = generated_path
        cache_image_file(assets_dir, cache_key, generated_path, os.path.splitext(generated_path)[1])
        print(f"[images] {scene_id}: saved to {generated_path}")

    manifest["image_map"] = image_map
    _save_manifest(manifest_path, manifest)
    build_spec(run_dir)
    return image_map


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate pilot scene images and rebuild the spec.")
    parser.add_argument("--run-dir", required=True, help="CiteVideo run directory")
    parser.add_argument(
        "--scene-id",
        action="append",
        dest="scene_ids",
        help="Scene ID to generate. Repeat for multiple scenes. Defaults to the curated pilot set.",
    )
    args = parser.parse_args()

    generate_images_for_run(args.run_dir, args.scene_ids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
