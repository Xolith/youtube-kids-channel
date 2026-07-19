"""
YouTube Kids Studio - Video Generation Pipeline
Used by backend to produce premium kids Shorts:
1. AI image per scene (via image_generate tool - FAL backend)
2. ElevenLabs natural TTS (Jessica voice)
3. FFmpeg montage: zoom + motion graphics + subtitles

All runs locally; no cloud DB. Status pushed to frontend via WebSocket.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
from pydub import AudioSegment
from PIL import Image, ImageDraw
import random

BASE = Path(__file__).resolve().parent.parent.parent  # YouTube project root
sys.path.insert(0, str(BASE / "scripts"))
sys.path.insert(0, str(BASE / "web" / "backend"))

# Import topics from main module dynamically (see generate_video)
# We don't import at module load time because main.TOPICS gets updated
# at runtime (AI-generated topics are added after server starts).
_TOPICS = {}

VID_DIR = BASE / "output" / "videos"
IMG_DIR = BASE / "output" / "images"
AUD_DIR = BASE / "output" / "audio"
FX_DIR = VID_DIR / "fx"
# AI-generated content directories
AI_IMG_DIR = IMG_DIR / "ai_generated"
AI_VID_DIR = VID_DIR / "animated"
FONT = "/Windows/Fonts/arial.ttf"

# ElevenLabs Jessica (warm child-friendly voice)
JESSICA_VOICE = "cgSgspJ2msm6clMCkdW9"


# -------------------------------------------------------------
#  ElevenLabs TTS
# -------------------------------------------------------------
def _load_eleven_key() -> str:
    env = BASE / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("ELEVENLABS_API_KEY="):
                return line.split("=", 1)[1].strip()
    return os.getenv("ELEVENLABS_API_KEY", "")


def generate_tts(text: str, out_path: str) -> str:
    import requests
    key = _load_eleven_key()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY not found in .env")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{JESSICA_VOICE}"
    headers = {"xi-api-key": key, "Content-Type": "application/json"}
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.75,
            "style": 0.6,
            "use_speaker_boost": True,
        },
    }
    r = requests.post(url, headers=headers, json=body, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs error {r.status_code}: {r.text[:200]}")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(r.content)
    return out_path


# -------------------------------------------------------------
#  AI image generation (via Hermes image_generate tool - FAL)
# -------------------------------------------------------------
# We cannot call the agent tool from here; this function is a hook.
# The backend websocket flow instead issues image_generate via the agent.
# For standalone usage, we save pre-existing images to img_dir.
def cinematic_prompt(brief: str) -> str:
    return (
        f"Cinematic 3D Pixar-quality render of {brief}, volumetric light, "
        f"subsurface scattering, octane render, 8k, dreamy cinematic lighting, "
        f"rich detail, 9:16 vertical"
    )

def kawaii_prompt(brief: str) -> str:
    return (
        f"3D cartoon kawaii style, {brief}, pastel background, rounded friendly shapes, "
        f"vibrant but soft colors, kids YouTube aesthetic, 9:16 vertical"
    )


# -------------------------------------------------------------
#  Motion graphics layers (PNG -> looping overlay video)
# -------------------------------------------------------------
def _make_bubble_layer():
    png = FX_DIR / "bubble.png"
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    random.seed(7)
    for _ in range(40):
        x, y = random.randint(20, 1060), random.randint(20, 1900)
        r = random.randint(6, 18)
        d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 255, 70), width=3)
    img.save(str(png))
    out = FX_DIR / "bubbles.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(png), "-frames:v", "300",
         "-vf", "format=rgba,split[a][b];[b]crop=1080:1920:0:0[a2];"
                "[a][a2]overlay=y='-mod(t*60,1920)'",
         "-c:v", "png", str(out)],
        capture_output=True,
    )
    return out

def _make_rays_layer():
    png = FX_DIR / "rays.png"
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    random.seed(3)
    for _ in range(6):
        x, w = random.randint(-100, 900), random.randint(40, 90)
        d.polygon([(x, 0), (x + w, 0), (x + w + 300, 1920), (x + 300, 1920)],
                  fill=(255, 255, 255, 22))
    img.save(str(png))
    out = FX_DIR / "rays.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(png), "-frames:v", "300",
         "-vf", "format=rgba,split[a][b];[b]crop=1080:1920:'min(mod(t*30,2000),1080)':0[a2];"
                "[a][a2]overlay=shortest=1",
         "-c:v", "png", str(out)],
        capture_output=True,
    )
    return out

def _make_sparkle_layer():
    png = FX_DIR / "sparkle.png"
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    random.seed(9)
    for _ in range(60):
        x, y = random.randint(20, 1060), random.randint(20, 1900)
        r = random.randint(2, 6)
        d.line([(x - r * 3, y), (x + r * 3, y)], fill=(255, 255, 200, 180), width=2)
        d.line([(x, y - r * 3), (x, y + r * 3)], fill=(255, 255, 200, 180), width=2)
    img.save(str(png))
    out = FX_DIR / "sparkles.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(png), "-frames:v", "300",
         "-vf", "format=rgba,split[a][b];[b]crop=1080:1920:0:'mod(t*45,1920)'[a2];"
                "[a][a2]overlay=shortest=1",
         "-c:v", "png", str(out)],
        capture_output=True,
    )
    return out


# -------------------------------------------------------------
#  Scene building
# -------------------------------------------------------------
def _dur(mp3: str) -> float:
    try:
        return AudioSegment.from_mp3(mp3).duration_seconds + 0.4
    except Exception:
        return 4.0

def _build_scene(img_path: str, aud_path: str, subtitle: str,
                 out_path: str, zoom: float, overlays: List[str],
                 animated_path: str = None) -> bool:
    d = _dur(aud_path)
    sub = (
        f"drawtext=text='{subtitle}':fontcolor=white:fontsize=64:fontfile={FONT}:"
        "box=1:boxcolor=black@0.5:boxborderw=20:x=(w-text_w)/2:y=h-180"
    )

    # If we have an AI-animated video, use it as the base instead of static image
    if animated_path and Path(animated_path).exists():
        base = (
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"zoompan=z='min(zoom+0.0005,{zoom})':d=1:"
            "x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920:fps=30"
        )
        if not overlays:
            vf = base + "," + sub
            cmd = ["ffmpeg", "-y", "-i", animated_path, "-i", aud_path,
                   "-vf", vf, "-t", str(d), "-c:v", "libx264", "-c:a", "aac",
                   "-b:a", "192k", "-pix_fmt", "yuv420p", out_path]
        else:
            fc = f"[0:v]{base}[bg]"
            last = "bg"
            for i, ly in enumerate(overlays):
                fc += f";[{i+1}:v]format=rgba[l{i}];[{last}][l{i}]overlay=shortest=1[o{i}]"
                last = f"o{i}"
            fc += f";[{last}]{sub}"
            inputs = ["-i", animated_path]
            for ly in overlays:
                inputs += ["-i", ly]
            inputs += ["-i", aud_path]
            cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", fc, "-t", str(d),
                   "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", out_path]
    else:
        # Static image with zoompan effect
        base = (
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"zoompan=z='min(zoom+0.0005,{zoom})':d=1:"
            "x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920:fps=30"
        )
        if not overlays:
            vf = base + "," + sub
            cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-i", aud_path,
                   "-vf", vf, "-t", str(d), "-c:v", "libx264", "-c:a", "aac",
                   "-b:a", "192k", "-pix_fmt", "yuv420p", out_path]
        else:
            fc = f"[0:v]{base}[bg]"
            last = "bg"
            for i, ly in enumerate(overlays):
                fc += f";[{i+1}:v]format=rgba[l{i}];[{last}][l{i}]overlay=shortest=1[o{i}]"
                last = f"o{i}"
            fc += f";[{last}]{sub}"
            inputs = ["-loop", "1", "-i", img_path]
            for ly in overlays:
                inputs += ["-i", ly]
            inputs += ["-i", aud_path]
            cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", fc, "-t", str(d),
                   "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0


# -------------------------------------------------------------
#  Main pipeline
# -------------------------------------------------------------
async def generate_video(topic_name: str, style: str, images_map: dict,
                         client_id: str, notify_fn) -> str:
    """images_map: {scene_id: png_path} - images must be pre-generated."""
    print(f"[pipeline] generate_video called: topic='{topic_name}', style='{style}', images_map keys={list(images_map.keys())}")
    # Dynamically import TOPICS from main so we see AI-generated topics
    # that were added at runtime (after the server started).
    try:
        import main as _main_mod
        topics_ref = _main_mod.TOPICS
    except Exception:
        topics_ref = _TOPICS
    print(f"[pipeline] TOPICS keys: {list(topics_ref.keys())}")
    if topic_name not in topics_ref:
        print(f"[pipeline] ERROR: topic '{topic_name}' not in TOPICS")
        raise ValueError(f"Unknown topic: {topic_name}")

    scenes = topics_ref[topic_name]["scenes"]
    print(f"[pipeline] Found {len(scenes)} scenes for topic '{topic_name}'")
    overlays_lookup = {
        "bubbles": str(FX_DIR / "bubbles.mp4"),
        "rays": str(FX_DIR / "rays.mp4"),
        "sparkles": str(FX_DIR / "sparkles.mp4"),
    }

    # Prepare motion graphics layers
    await notify_fn(client_id, "preparing", "Motion graphics katmanlari hazirlaniyor...", 5)
    _make_bubble_layer()
    _make_rays_layer()
    _make_sparkle_layer()

    clips = []
    total = len(scenes)
    for i, scene in enumerate(scenes, 1):
        sid, narration, subtitle, use_bubbles, use_rays = scene
        pct = 10 + int((i / total) * 80)

        # TTS
        await notify_fn(client_id, "tts", f"[{i}/{total}] Ses uretiliyor: {sid}", pct)
        audio_path = AUD_DIR / f"{topic_name.replace(' ','_').lower()}_{sid}.mp3"
        if not audio_path.exists():
            generate_tts(narration, str(audio_path))

        # Image lookup: AI-generated first, then uploaded, then flexible match
        img_path = images_map.get(sid)
        if not img_path or not Path(img_path).exists():
            # Check AI-generated images directory
            ai_topic_dir = AI_IMG_DIR / topic_name.replace(" ", "_").lower()
            ai_img = ai_topic_dir / f"{sid}.png"
            if ai_img.exists():
                img_path = str(ai_img)
            else:
                # Try partial match in AI dir
                candidates = []
                if ai_topic_dir.exists():
                    for p in ai_topic_dir.glob("*.png"):
                        if sid in p.stem or p.stem.startswith(sid.split("_")[0] + "_"):
                            candidates.append(str(p))
                # Also check uploaded images dir
                topic_img_dir = IMG_DIR / topic_name.replace(" ", "_").lower()
                if not candidates and topic_img_dir.exists():
                    for p in topic_img_dir.glob("*.png"):
                        if sid in p.stem or p.stem.startswith(sid.split("_")[0] + "_"):
                            candidates.append(str(p))
                if candidates:
                    img_path = candidates[0]
                else:
                    raise RuntimeError(f"Image missing for scene {sid}")

        # Check for AI-animated video (use it instead of static image if available)
        ai_vid_path = AI_VID_DIR / topic_name.replace(" ", "_").lower() / f"{sid}.mp4"
        use_animated = ai_vid_path.exists()

        # Overlays for this scene
        overlays = []
        if use_bubbles:
            overlays.append(overlays_lookup["bubbles"])
        if use_rays:
            overlays.append(overlays_lookup["rays"])

        # Build scene
        await notify_fn(client_id, "build", f"[{i}/{total}] Sahne montaji: {sid}", pct + 5)
        out_clip = VID_DIR / f"{topic_name.replace(' ','_').lower()}_{sid}.mp4"
        animated = str(ai_vid_path) if use_animated else None
        ok = _build_scene(str(img_path), str(audio_path), subtitle,
                          str(out_clip), zoom=1.06 + (i % 3) * 0.01, overlays=overlays,
                          animated_path=animated)
        if not ok:
            raise RuntimeError(f"Scene build failed: {sid}")
        clips.append(str(out_clip))

    # Concatenate
    await notify_fn(client_id, "concat", "Videolar birlestiriliyor...", 92)
    concat_file = VID_DIR / f"{topic_name.replace(' ','_').lower()}_concat.txt"
    with open(concat_file, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    final = VID_DIR / f"{topic_name.replace(' ','_').lower()}_{style}.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
         "-c", "copy", str(final)],
        capture_output=True,
    )

    await notify_fn(client_id, "done", f"Video hazir: {final.name}", 100)
    return str(final)