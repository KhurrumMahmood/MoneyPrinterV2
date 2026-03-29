import os
import sys
import json
import argparse
import requests
import uuid
from dotenv import load_dotenv

# Load environment
load_dotenv()

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_KEY = os.environ.get("OPENROUTER_API_KEY")
BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
MODEL = os.environ.get("OPENROUTER_SCRIPT_MODEL", "google/gemini-3.1-pro-preview")

if not API_KEY:
    print("ERROR: OPENROUTER_API_KEY not found in environment.")
    sys.exit(1)

def generate_script(topic: str, run_id: str) -> dict:
    print(f"Generating educational video script for topic: {topic}")
    
    system_prompt = """
You are a master science communicator and documentary producer. Your task is to write a highly engaging, scientifically accurate micro-documentary script for YouTube Shorts/TikTok.

You must output a raw, parseable JSON object. DO NOT wrap the output in Markdown code blocks (e.g. ```json). Your entire response must be standard JSON.

The structural template looks exactly like this:
{
  "meta": {
    "runId": "%run_id%",
    "title": "A compelling, viral-style title about the topic",
    "fps": 30,
    "width": 1080,
    "height": 1920
  },
  "brand": {
    "colors": {
      "primary": "#0f1419",
      "secondary": "#1a2332",
      "accent": "#14b8a6",
      "text": "#f0ece4",
      "textSecondary": "#94a3b8",
      "success": "#22c55e",
      "warning": "#f59e0b",
      "danger": "#fb7185"
    },
    "fonts": {
      "heading": "Inter",
      "body": "Inter"
    }
  },
  "audio": {},
  "scenes": [
    {
      "sceneId": "scene_001",
      "type": "title",
      "heading": "Short scene heading",
      "narration": "The exact script to be read. Must be conversational, empathetic, and engaging. No overly robotic clinical terms unless explained.",
      "mood": "curiosity",
      "evidenceStrength": "high",
      "evidenceColor": "#14b8a6",
      "visualNotes": "Detailed prompt for an image generator (e.g., Gemini Flash). Must specify: 'Warm, professional health science illustration. Soft lighting with teal and warm amber accents on a dark background. No text. 16:9 aspect ratio.' plus the specific subjects.",
      "keywords": ["Hook", "Topic", "Concept"]
    },
    ...
  ]
}

Rules for the Content:
1. Divide the video into 3 to 4 scenes. Scene 1 should be 'title', Scene 2 'talking_point', Scene 3 'image', etc.
2. Ensure the narration uses conversational pacing. Include pauses implicitly through punctuation.
3. Your final output MUST be purely valid JSON.
"""
    system_prompt = system_prompt.replace("%run_id%", run_id)

    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Write a video script about: {topic}"}
            ],
            "response_format": { "type": "json_object" }
        },
        timeout=120,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Script API error {response.status_code}: {response.text[:300]}")

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
        # In case the model still outputs markdown blocks, strip them
        content = content.replace("```json", "").replace("```", "").strip()
        spec = json.loads(content)
        return spec
    except (KeyError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Failed to parse LLM response into JSON: {e}\nRaw Response: {data}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=str, required=True, help="Topic for the video")
    parser.add_argument("--id", type=str, help="Unique ID for the project directory", default="")
    args = parser.parse_args()

    project_id = args.id if args.id else str(uuid.uuid4())[:8]
    
    # Path handling
    public_dir = os.path.join(ROOT, "remotion", "public", project_id)
    os.makedirs(public_dir, exist_ok=True)
    
    spec_path = os.path.join(public_dir, "spec.json")
    
    try:
        spec_data = generate_script(args.topic, project_id)
        with open(spec_path, "w") as f:
            json.dump(spec_data, f, indent=2)
        print(f"SUCCESS. Spec created at: {spec_path}")
    except Exception as e:
        print(f"FAILED to generate script: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
