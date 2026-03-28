"""
Content-hash-based caching for paid-media artifacts.
"""

from __future__ import annotations

import hashlib
import os
import shutil


def build_cache_key(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update((part or "").encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _cache_path(assets_dir: str, bucket: str, key: str, ext: str) -> str:
    cache_dir = os.path.join(assets_dir, "cache", bucket)
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{key}{ext}")


def restore_cached_file(assets_dir: str, bucket: str, key: str, ext: str, output_path: str) -> bool:
    cached_path = _cache_path(assets_dir, bucket, key, ext)
    if not os.path.exists(cached_path):
        return False
    shutil.copy2(cached_path, output_path)
    return True


def cache_audio_file(assets_dir: str, key: str, source_path: str, ext: str = ".wav") -> str:
    cached_path = _cache_path(assets_dir, "audio", key, ext)
    shutil.copy2(source_path, cached_path)
    return cached_path


def cache_text_file(assets_dir: str, key: str, source_path: str, ext: str = ".srt") -> str:
    cached_path = _cache_path(assets_dir, "transcripts", key, ext)
    shutil.copy2(source_path, cached_path)
    return cached_path


def cache_image_file(assets_dir: str, key: str, source_path: str, ext: str) -> str:
    cached_path = _cache_path(assets_dir, "images", key, ext)
    shutil.copy2(source_path, cached_path)
    return cached_path
