"""
YouTube Kids Studio - AI Generator Module
Handles:
1. OpenRouter API for AI topic generation (free models)
2. Hugging Face Inference API for image generation
3. Hugging Face image-to-video animation
"""

import os
import json
import base64
import random
import requests
from pathlib import Path
from typing import List, Dict, Optional

BASE = Path(__file__).resolve().parent.parent.parent  # YouTube project root

# Directories for AI-generated content
AI_IMG_DIR = BASE / "output" / "images" / "ai_generated"
AI_VID_DIR = BASE / "output" / "videos" / "animated"
for d in (AI_IMG_DIR, AI_VID_DIR):
    d.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------------
#  .env loader
# -------------------------------------------------------------
def _load_env() -> dict:
    """Load .env file into a dict."""
    env_path = BASE / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    # Also merge os.environ (takes precedence)
    for k in ("OPENROUTER_API_KEY", "HF_TOKEN", "HF_API_KEY", "ELEVENLABS_API_KEY", "PIXABAY_API_KEY"):
        if k in os.environ:
            env[k] = os.environ[k]
    return env


# -------------------------------------------------------------
#  OpenRouter - AI Topic Generation
# -------------------------------------------------------------
# Free models on OpenRouter (verified 2026-07 via /api/v1/models):
# NOTE: Gemini free variants were removed upstream (now paid only).
# Current free models that work for topic generation:
# - google/gemma-4-31b-it:free       (recommended, Google's latest Gemma)
# - nvidia/nemotron-3-ultra-550b-a55b:free  (largest, most capable)
# - nvidia/nemotron-3-super-120b-a12b:free
# - nvidia/nemotron-3-nano-30b-a3b:free
# - openai/gpt-oss-20b:free
# - google/gemma-4-26b-a4b-it:free

DEFAULT_MODEL = "google/gemma-4-31b-it:free"

# Fallback chain: if the primary model is rate-limited (429) or unavailable
# (404), automatically try the next models in order. This makes topic
# generation resilient to temporary upstream rate-limits and models being
# removed from the free tier.
FALLBACK_MODELS = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "openai/gpt-oss-20b:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "google/gemma-4-26b-a4b-it:free",
]

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _get_openrouter_key() -> str:
    env = _load_env()
    key = env.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not found in .env")
    return key


def _call_openrouter(key: str, model: str, system_prompt: str, user_message: str) -> str:
    """Single OpenRouter call. Returns raw content string. Raises RuntimeError on non-429 errors."""
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8001",
        "X-Title": "YouTube Kids Studio",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.8,
        "max_tokens": 2000,
    }
    r = requests.post(OPENROUTER_URL, headers=headers, json=body, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"OpenRouter error {r.status_code}: {r.text[:300]}")
    data = r.json()
    return data["choices"][0]["message"]["content"]


def generate_topic_with_ai(user_prompt: str, model: str = DEFAULT_MODEL) -> dict:
    """
    Use OpenRouter to generate a kids-friendly topic with scenes.
    Returns a dict matching the TOPICS structure:
    {
        "name": "Topic Name",
        "description": "Short description",
        "scenes": [
            ["01_intro", "narration text", "SUBTITLE", true/false, true/false],
            ...
        ]
    }

    If the requested model is rate-limited (429), automatically falls back
    to other free models in FALLBACK_MODELS so generation stays resilient.
    """
    key = _get_openrouter_key()

    system_prompt = """You are a YouTube Kids Shorts content creator. Generate engaging, educational, and fun content for children aged 4-10.

You must respond with ONLY valid JSON (no markdown, no code blocks, no explanation) in this exact format:
{
  "name": "Topic Name (2-3 words, Title Case)",
  "description": "Short engaging description (5-8 words)",
  "scenes": [
    ["01_intro", "Hey little explorers! Welcome to [topic]. Today we have amazing facts. Ready? Let's go!", "WELCOME!", true, true],
    ["02_scene1", "Fun fact narration text (2-3 sentences, kid-friendly)", "Short subtitle!", false, true],
    ["03_scene2", "Another fun fact narration", "Subtitle!", true, false],
    ["04_scene3", "Another fun fact narration", "Subtitle!", false, true],
    ["05_scene4", "Another fun fact narration", "Subtitle!", true, false],
    ["06_scene5", "Another fun fact narration", "Subtitle!", false, true],
    ["07_outro", "Did you love these facts? Hit subscribe and join us next time. Bye bye!", "SUBSCRIBE!", true, true]
  ]
}

Rules:
- Exactly 7 scenes (intro, 5 facts, outro)
- Each scene: [scene_id, narration, subtitle, use_bubbles (bool), use_rays (bool)]
- Narration should be 2-3 sentences, enthusiastic, kid-friendly
- Subtitles should be short (2-4 words, uppercase)
- Alternate bubbles/rays for visual variety
- Topic must be educational and safe for kids
- Respond with ONLY the JSON, nothing else"""

    user_message = f"Create a YouTube Kids Shorts topic about: {user_prompt}"

    # Build the list of models to try: the requested model first, then the
    # rest of the fallback chain (deduplicated, preserving order).
    try_models = [model]
    for m in FALLBACK_MODELS:
        if m not in try_models:
            try_models.append(m)

    last_error = None
    for m in try_models:
        try:
            content = _call_openrouter(key, m, system_prompt, user_message)
        except RuntimeError as e:
            msg = str(e)
            last_error = e
            # 429 = rate limited upstream -> try next model automatically
            if "429" in msg:
                print(f"[ai_generator] Model {m} rate-limited (429), trying next fallback...")
                continue
            # 404 = model unavailable/removed from free tier -> try next model
            if "404" in msg:
                print(f"[ai_generator] Model {m} unavailable (404), trying next fallback...")
                continue
            # Any other error (auth, 5xx that isn't transient, etc.) -> raise immediately
            raise
        # Success
        if m != model:
            print(f"[ai_generator] Fallback succeeded with model: {m}")
        break
    else:
        # All models exhausted
        raise RuntimeError(
            f"All models rate-limited or unavailable. Last error: {last_error}"
        )

    # Strip markdown code blocks if present
    content = content.strip()
    if content.startswith("```"):
        # Remove ```json or ``` at start and ``` at end
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    topic_data = json.loads(content)

    # Validate structure
    if "name" not in topic_data or "scenes" not in topic_data:
        raise ValueError("AI response missing required fields (name, scenes)")

    if len(topic_data["scenes"]) != 7:
        # Pad or trim to 7 scenes
        while len(topic_data["scenes"]) < 7:
            topic_data["scenes"].append(
                [f"0{len(topic_data['scenes'])+1}_scene", "Amazing fact!", "Fun!", False, True]
            )
        topic_data["scenes"] = topic_data["scenes"][:7]

    # Ensure scene format: convert booleans properly
    normalized_scenes = []
    for i, scene in enumerate(topic_data["scenes"], 1):
        if len(scene) >= 5:
            sid = scene[0]
            narration = scene[1]
            subtitle = scene[2]
            use_bubbles = bool(scene[3])
            use_rays = bool(scene[4])
            normalized_scenes.append([sid, narration, subtitle, use_bubbles, use_rays])
        else:
            # Fallback
            normalized_scenes.append([
                f"0{i}_scene",
                scene[1] if len(scene) > 1 else "Fun fact!",
                scene[2] if len(scene) > 2 else "Fun!",
                bool(scene[3]) if len(scene) > 3 else False,
                bool(scene[4]) if len(scene) > 4 else True,
            ])

    topic_data["scenes"] = normalized_scenes
    return topic_data


# -------------------------------------------------------------
#  Image Generation (Hugging Face + Pollinations fallback)
# -------------------------------------------------------------
HF_INFERENCE_URL = "https://api-inference.huggingface.co/models"

# Free image generation models on HF
IMAGE_MODELS = {
    "flux-schnell": "black-forest-labs/FLUX.1-schnell",
    "sdxl": "stabilityai/stable-diffusion-xl-base-1.0",
    "sd-1.5": "runwayml/stable-diffusion-v1-5",
}

DEFAULT_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"

# Pollinations.ai - completely free, no API key required
POLLINATIONS_URL = "https://image.pollinations.ai/prompt"


def _get_hf_key() -> str:
    env = _load_env()
    # Accept both HF_TOKEN (standard) and HF_API_KEY (legacy)
    key = env.get("HF_TOKEN", "") or env.get("HF_API_KEY", "")
    if not key:
        raise RuntimeError("HF_TOKEN not found in .env")
    return key


def _generate_via_pollinations(prompt: str, out_path: str) -> str:
    """Generate an image using Pollinations.ai (free, no API key needed)."""
    import urllib.parse
    import time

    encoded_prompt = urllib.parse.quote(prompt)
    url = f"{POLLINATIONS_URL}/{encoded_prompt}?width=1080&height=1920&model=flux&nologo=true&seed={random.randint(1, 999999)}"

    for attempt in range(3):
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200 and len(r.content) > 1000:
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(r.content)
                print(f"[ai_generator] Image generated via Pollinations.ai")
                return out_path
            else:
                print(f"[ai_generator] Pollinations attempt {attempt+1} failed: status={r.status_code}, size={len(r.content)}")
                time.sleep(5)
        except Exception as e:
            print(f"[ai_generator] Pollinations attempt {attempt+1} error: {e}")
            time.sleep(5)

    raise RuntimeError("Pollinations image generation failed after 3 attempts")


def generate_image(prompt: str, out_path: str, model: str = DEFAULT_IMAGE_MODEL) -> str:
    """Generate an image using Hugging Face Inference API with Pollinations fallback."""
    # Try Hugging Face first (if API key available)
    try:
        key = _get_hf_key()
        model_id = IMAGE_MODELS.get(model, model)
        url = f"{HF_INFERENCE_URL}/{model_id}"

        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        body = {"inputs": prompt}

        for attempt in range(3):
            r = requests.post(url, headers=headers, json=body, timeout=90)
            if r.status_code == 200:
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(r.content)
                print(f"[ai_generator] Image generated via Hugging Face")
                return out_path
            elif r.status_code == 503:
                import time
                time.sleep(10)
                continue
            else:
                print(f"[ai_generator] HF error {r.status_code}, falling back to Pollinations")
                break

    except RuntimeError as e:
        if "HF_TOKEN" in str(e):
            print(f"[ai_generator] No HF_TOKEN found, using Pollinations.ai directly")
        else:
            print(f"[ai_generator] HF failed ({e}), falling back to Pollinations")
    except Exception as e:
        print(f"[ai_generator] HF failed ({e}), falling back to Pollinations")

    # Fallback: Pollinations.ai (free, no API key)
    return _generate_via_pollinations(prompt, out_path)


def generate_scene_images(topic_name: str, scenes: list, style: str = "cinematic") -> dict:
    """
    Generate images for all scenes of a topic.
    Returns {scene_id: image_path}
    """
    topic_dir = AI_IMG_DIR / topic_name.replace(" ", "_").lower()
    topic_dir.mkdir(parents=True, exist_ok=True)

    images_map = {}
    for scene in scenes:
        sid = scene[0]
        narration = scene[1]

        # Build prompt based on style
        if style == "kawaii":
            prompt = (
                f"3D cartoon kawaii style, {narration[:100]}, pastel background, "
                f"rounded friendly shapes, vibrant soft colors, kids YouTube aesthetic, "
                f"vertical 9:16, high quality"
            )
        else:
            prompt = (
                f"Cinematic 3D Pixar-quality render, {narration[:100]}, volumetric light, "
                f"subsurface scattering, dreamy cinematic lighting, rich detail, "
                f"vertical 9:16, 8k"
            )

        out_path = topic_dir / f"{sid}.png"
        if not out_path.exists():
            generate_image(prompt, str(out_path))

        images_map[sid] = str(out_path)

    return images_map


# -------------------------------------------------------------
#  Hugging Face - Image-to-Video Animation
# -------------------------------------------------------------
# Image-to-video models on HF (may require Pro account)
VIDEO_MODELS = {
    "svd-xt": "stabilityai/stable-video-diffusion-img2vid-xt",
    "svd": "stabilityai/stable-video-diffusion-img2vid",
}

DEFAULT_VIDEO_MODEL = "stabilityai/stable-video-diffusion-img2vid-xt"


def animate_image(image_path: str, out_path: str, motion_scale: int = 6) -> str:
    """
    Animate a static image using Hugging Face image-to-video model.
    Requires HF_API_KEY with access to stable-video-diffusion models.

    NOTE: This may require a Hugging Face Pro account.
    If it fails, the pipeline falls back to zoompan effect in FFmpeg.
    """
    key = _get_hf_key()
    url = f"{HF_INFERENCE_URL}/{DEFAULT_VIDEO_MODEL}"

    headers = {"Authorization": f"Bearer {key}"}

    with open(image_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()

    body = {
        "inputs": img_data,
        "parameters": {
            "motion_bucket_id": motion_scale,  # 1-127, higher = more motion
            "cond_aug": 0.02,
            "decoding_t": 7,
            "video_length": 14,  # frames
            "fps": 4,
        }
    }

    for attempt in range(3):
        r = requests.post(url, headers=headers, json=body, timeout=120)
        if r.status_code == 200:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(r.content)
            return out_path
        elif r.status_code == 503:
            import time
            time.sleep(15)
            continue
        else:
            raise RuntimeError(f"HF video error {r.status_code}: {r.text[:300]}")

    raise RuntimeError("HF video animation failed after 3 attempts")


def animate_scene_images(topic_name: str, images_map: dict) -> dict:
    """
    Animate all scene images.
    Returns {scene_id: video_path}
    """
    topic_vid_dir = AI_VID_DIR / topic_name.replace(" ", "_").lower()
    topic_vid_dir.mkdir(parents=True, exist_ok=True)

    animated_map = {}
    for sid, img_path in images_map.items():
        vid_path = topic_vid_dir / f"{sid}.mp4"
        if not vid_path.exists():
            try:
                animate_image(img_path, str(vid_path))
            except RuntimeError as e:
                # Fallback: return None, pipeline will use zoompan
                print(f"Animation failed for {sid}: {e}")
                animated_map[sid] = None
                continue
        animated_map[sid] = str(vid_path)

    return animated_map


# -------------------------------------------------------------
#  List available free models
# -------------------------------------------------------------
def get_available_models() -> dict:
    """Return available free models for the frontend."""
    return {
        "topic_models": [
            {"id": "google/gemma-4-31b-it:free", "name": "Gemma 4 31B (Free)", "recommended": True},
            {"id": "nvidia/nemotron-3-ultra-550b-a55b:free", "name": "Nemotron 3 Ultra 550B (Free)"},
            {"id": "nvidia/nemotron-3-super-120b-a12b:free", "name": "Nemotron 3 Super 120B (Free)"},
            {"id": "openai/gpt-oss-20b:free", "name": "GPT OSS 20B (Free)"},
            {"id": "nvidia/nemotron-3-nano-30b-a3b:free", "name": "Nemotron 3 Nano 30B (Free)"},
            {"id": "google/gemma-4-26b-a4b-it:free", "name": "Gemma 4 26B (Free)"},
        ],
        "image_models": [
            {"id": "flux-schnell", "name": "FLUX.1 Schnell (Fast, Free)", "recommended": True},
            {"id": "sdxl", "name": "Stable Diffusion XL (Free)"},
            {"id": "sd-1.5", "name": "Stable Diffusion 1.5 (Free)"},
        ],
        "video_models": [
            {"id": "svd-xt", "name": "Stable Video Diffusion XT (Requires HF Pro)", "recommended": True},
            {"id": "svd", "name": "Stable Video Diffusion (Requires HF Pro)"},
        ],
    }