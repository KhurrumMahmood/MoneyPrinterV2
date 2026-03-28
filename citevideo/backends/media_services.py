"""
Concrete paid-media backends used by asset generation.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import wave

import requests

from citevideo.backends.media import AudioBackend, ImageBackend, TranscriptionBackend
from citevideo.config import (
    get_openrouter_api_key,
    get_openrouter_audio_model,
    get_openrouter_base_url,
)


def _get_openrouter_base() -> str:
    return get_openrouter_base_url().rstrip("/")


class OpenRouterAudioBackend(AudioBackend):
    def synthesize(self, text: str, output_path: str) -> str:
        response = requests.post(
            f"{_get_openrouter_base()}/chat/completions",
            headers={
                "Authorization": f"Bearer {get_openrouter_api_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": get_openrouter_audio_model() or "openai/tts-1-hd",
                "stream": True,
                "modalities": ["text", "audio"],
                "audio": {"voice": "alloy", "format": "pcm16"},
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Read this text aloud exactly as written, with natural pacing and expression:\n\n"
                            f"{text}"
                        ),
                    }
                ],
            },
            stream=True,
            timeout=600,
        )
        if response.status_code != 200:
            raise RuntimeError(f"TTS API returned {response.status_code}: {response.text[:500]}")

        audio_b64_chunks: list[str] = []
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            for choice in chunk.get("choices", []):
                delta = choice.get("delta", {})
                audio = delta.get("audio", {})
                if audio.get("data"):
                    audio_b64_chunks.append(audio["data"])

        if not audio_b64_chunks:
            raise RuntimeError("TTS returned no audio data")

        pcm_bytes = base64.b64decode("".join(audio_b64_chunks))
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm_bytes)
        return output_path


class WhisperLocalBackend(TranscriptionBackend):
    def transcribe(self, audio_path: str, output_path: str) -> str:
        try:
            import whisper
        except ImportError:
            subprocess.run(
                ["whisper", audio_path, "--output_format", "srt", "--output_dir", os.path.dirname(output_path)],
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )
            generated = os.path.join(
                os.path.dirname(output_path),
                f"{os.path.splitext(os.path.basename(audio_path))[0]}.srt",
            )
            if generated != output_path and os.path.exists(generated):
                with open(generated, "r", encoding="utf-8") as src, open(
                    output_path, "w", encoding="utf-8"
                ) as dst:
                    dst.write(src.read())
            return output_path

        model = whisper.load_model("base")
        result = model.transcribe(audio_path, word_timestamps=True)
        srt_lines = []
        for i, seg in enumerate(result.get("segments", []), 1):
            start = seg["start"]
            end = seg["end"]
            text = seg["text"].strip()
            start_str = (
                f"{int(start // 3600):02d}:{int((start % 3600) // 60):02d}:"
                f"{int(start % 60):02d},{int((start % 1) * 1000):03d}"
            )
            end_str = (
                f"{int(end // 3600):02d}:{int((end % 3600) // 60):02d}:"
                f"{int(end % 60):02d},{int((end % 1) * 1000):03d}"
            )
            srt_lines.extend([str(i), f"{start_str} --> {end_str}", text, ""])

        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(srt_lines))
        return output_path


class OpenRouterImageBackend(ImageBackend):
    def generate(self, prompt: str, output_path: str) -> str:
        response = requests.post(
            f"{_get_openrouter_base()}/chat/completions",
            headers={
                "Authorization": f"Bearer {get_openrouter_api_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": "google/gemini-3.1-flash-image-preview",
                "messages": [{"role": "user", "content": prompt}],
                "modalities": ["image", "text"],
            },
            timeout=120,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Image API returned {response.status_code}: {response.text[:200]}"
            )
        data = response.json()

        for choice in data.get("choices", []):
            parts = choice.get("message", {}).get("content", [])
            if not isinstance(parts, list):
                continue
            for part in parts:
                if not isinstance(part, dict) or part.get("type") != "image_url":
                    continue
                img_data = part.get("image_url", {}).get("url", "")
                if not img_data.startswith("data:"):
                    continue
                b64 = img_data.split(",", 1)[1]
                ext = ".png"
                if "jpeg" in img_data or "jpg" in img_data:
                    ext = ".jpg"
                actual_output = os.path.splitext(output_path)[0] + ext
                with open(actual_output, "wb") as handle:
                    handle.write(base64.b64decode(b64))
                return actual_output

        raise RuntimeError("Image response did not include an image payload")
