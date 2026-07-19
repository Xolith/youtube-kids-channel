"""
YouTube Kids Studio - Backend API
Premium web application for generating YouTube Kids Shorts
Architecture: FastAPI + FFmpeg + ElevenLabs + FAL (via Hermes tools)
No Supabase/Firebase - everything local (no cost)
"""

import os
import sys
import json
import uuid
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Resolve project paths
# This file: web/backend/main.py
# BASE should be the YouTube project root (contains output/, scripts/, web/)
BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE / "scripts"))
sys.path.insert(0, str(BASE / "web" / "backend"))

# AI generator module
from ai_generator import (
    generate_topic_with_ai,
    generate_scene_images,
    animate_scene_images,
    get_available_models,
)

VID_DIR = BASE / "output" / "videos"
IMG_DIR = BASE / "output" / "images"
AUD_DIR = BASE / "output" / "audio"
FX_DIR = VID_DIR / "fx"
for d in (VID_DIR, IMG_DIR, AUD_DIR, FX_DIR):
    d.mkdir(parents=True, exist_ok=True)

FONT = "/Windows/Fonts/arial.ttf"

app = FastAPI(title="YouTube Kids Studio", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
#  MODELS
# ============================================================

class GenerateRequest(BaseModel):
    topic: str = "Ocean Animals"
    style: str = "cinematic"  # cinematic | kawaii
    voice: str = "jessica"  # jessica only for now (free ElevenLabs)
    music_url: Optional[str] = None
    scenes_json: Optional[str] = None  # user-provided scene definition
    client_id: str = ""  # for WebSocket progress

# Predefined kids content topics
TOPICS = {
    "Ocean Animals": {
        "description": "Amazing facts about sea creatures",
        "scenes": [
            ("01_intro", "Hey little explorers! Welcome to the ocean adventure. Today we have five super cool sea animal facts. Ready? Let's dive in!", "OCEAN ADVENTURE", True, True),
            ("02_octopus", "Did you know an octopus has not one, not two, but THREE hearts! Can you feel yours? Boom boom.", "Octopus = 3 hearts!", False, True),
            ("03_dolphin", "Dolphins have their very own names! They whistle a special tune so their friends know it's them. Smart, right?", "Dolphins have names!", True, False),
            ("04_starfish", "If a starfish loses an arm, it just grows a new one. Like magic! Good as new in no time.", "Starfish regrows!", False, True),
            ("05_seahorse", "Daddy seahorse carries the babies! He keeps them safe in his tummy until they are ready to swim. Go super dad!", "Daddy carries babies!", True, False),
            ("06_whale", "The blue whale has the biggest heart on Earth. It is as large as a small car! Thump thump!", "Biggest heart ever!", False, False),
            ("07_outro", "Did you love these ocean facts? Hit subscribe and join us next time, under the sea. Bye bye!", "SUBSCRIBE under the sea!", True, True),
        ]
    },
    "Space Adventure": {
        "description": "Mind-blowing facts about space",
        "scenes": [
            ("01_intro", "Hey explorers! Welcome to Space Adventures! Get ready for five amazing space facts that will blow your mind. Let's go!", "SPACE ADVENTURES", True, True),
            ("02_sleep", "Astronauts can sleep standing up in space! With no gravity, they just float and snooze anywhere!", "Sleep standing up!", True, False),
            ("03_venus", "Venus is the hottest planet. It is even hotter than Mercury, even though it is farther from the Sun. Wow!", "Venus is hottest!", False, True),
            ("04_stars", "There are more stars in the sky than grains of sand on the whole Earth. Count them if you can!", "More stars than sand!", True, False),
            ("05_neptune", "Neptune has the fastest winds in the solar system. They whoosh at 1800 kilometers per hour!", "Winds of Neptune!", False, True),
            ("06_float", "In space, you would grow about 5 centimeters taller. No gravity means your spine stretches out!", "You grow taller!", True, False),
            ("07_outro", "Did you learn something amazing? Hit subscribe and we will see you among the stars. Bye!", "SUBSCRIBE for more!", True, True),
        ]
    },
}

# ============================================================
#  ROUTES
# ============================================================

@app.get("/api/topics")
def get_topics():
    return {
        "topics": [
            {"name": k, "description": v["description"], "scene_count": len(v["scenes"])}
            for k, v in TOPICS.items()
        ]
    }

@app.get("/api/topic/{topic_name}")
def get_topic(topic_name: str):
    if topic_name not in TOPICS:
        raise HTTPException(404, "Topic not found")
    return {"name": topic_name, "scenes": TOPICS[topic_name]["scenes"]}

@app.get("/api/history")
def get_history():
    """List all generated videos."""
    videos = []
    for f in sorted(VID_DIR.glob("*.mp4"), key=os.path.getmtime, reverse=True):
        stat = f.stat()
        videos.append({
            "filename": f.name,
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
            "created": stat.st_mtime,
        })
    return {"videos": videos[:20]}  # last 20

@app.get("/api/download/{filename}")
def download(filename: str):
    path = VID_DIR / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(path), media_type="video/mp4", filename=filename)

@app.get("/api/preview/{filename}")
def preview(filename: str):
    path = VID_DIR / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(path), media_type="video/mp4")

# WebSocket endpoint for real-time progress
# Frontend opens this, then POSTs to /api/generate - backend pushes progress
progress_clients = {}

@app.websocket("/ws/progress")
async def ws_progress(ws: WebSocket):
    await ws.accept()
    client_id = str(uuid.uuid4())
    progress_clients[client_id] = ws
    await ws.send_json({"type": "connected", "client_id": client_id})
    try:
        while True:
            _ = await ws.receive_text()
    except WebSocketDisconnect:
        progress_clients.pop(client_id, None)

async def notify(client_id: str, stage: str, msg: str, progress: int):
    ws = progress_clients.get(client_id)
    if ws:
        await ws.send_json({"stage": stage, "message": msg, "progress": progress})

# Generation endpoint with real-time WebSocket progress
async def background_generate(topic: str, style: str, client_id: str, images_map: dict):
    from pipeline import generate_video
    try:
        print(f"[generate] Starting video generation for topic='{topic}', style='{style}', images={list(images_map.keys())}")
        await generate_video(topic, style, images_map, client_id, notify)
        print(f"[generate] Video generation completed for topic='{topic}'")
    except Exception as e:
        import traceback
        print(f"[generate] ERROR: {e}")
        traceback.print_exc()
        await notify(client_id, "error", str(e), -1)


@app.post("/api/generate")
async def generate(req: GenerateRequest, bg: BackgroundTasks):
    topic = req.topic
    style = req.style
    client_id = req.client_id
    img_map = {}
    # Look in topic image dir
    topic_dir = IMG_DIR / topic.replace(" ", "_").lower()
    if topic_dir.exists():
        for p in topic_dir.glob("*.png"):
            sid = p.stem
            img_map[sid] = str(p)
    # Also allow a scenes_json override mapping scene suffix -> filename
    if req.scenes_json:
        try:
            custom = json.loads(req.scenes_json)
            for k, v in custom.items():
                img_map[k] = v
        except Exception:
            pass
    if not img_map:
        raise HTTPException(400, "No images uploaded. Use /api/upload first.")
    bg.add_task(background_generate, topic, style, client_id, img_map)
    return {"status": "started", "client_id": client_id, "scenes": len(img_map)}

@app.post("/api/upload/{scene_id}/{topic}")
async def upload_image(scene_id: str, topic: str, file: UploadFile = File(...)):
    topic_dir = IMG_DIR / topic.replace(" ", "_").lower()
    topic_dir.mkdir(parents=True, exist_ok=True)
    path = topic_dir / f"{scene_id}.png"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"saved": str(path), "size_kb": path.stat().st_size // 1024}


# ============================================================
#  AI GENERATION ENDPOINTS
# ============================================================

class AITopicRequest(BaseModel):
    prompt: str
    model: str = "google/gemma-4-31b-it:free"


@app.get("/api/ai/models")
def ai_models():
    """List available free AI models."""
    return get_available_models()


@app.post("/api/ai/generate-topic")
async def ai_generate_topic(req: AITopicRequest):
    """Generate a topic with scenes using OpenRouter AI."""
    try:
        topic_data = generate_topic_with_ai(req.prompt, req.model)
        # Add to TOPICS dict so it's available for generation
        TOPICS[topic_data["name"]] = {
            "description": topic_data["description"],
            "scenes": [tuple(s) for s in topic_data["scenes"]],
        }
        return topic_data
    except Exception as e:
        raise HTTPException(500, str(e))


class AIImageRequest(BaseModel):
    topic: str
    style: str = "cinematic"
    client_id: str = ""


@app.post("/api/ai/generate-images")
async def ai_generate_images(req: AIImageRequest, bg: BackgroundTasks):
    """Generate images for all scenes of a topic using Hugging Face."""
    if req.topic not in TOPICS:
        raise HTTPException(404, "Topic not found")
    scenes = TOPICS[req.topic]["scenes"]
    bg.add_task(background_generate_images, req.topic, req.style, scenes, req.client_id)
    return {"status": "started", "topic": req.topic, "scene_count": len(scenes)}


async def background_generate_images(topic: str, style: str, scenes: list, client_id: str):
    """Background task to generate images and notify via WebSocket."""
    try:
        total = len(scenes)
        for i, scene in enumerate(scenes, 1):
            sid = scene[0]
            pct = int((i / total) * 100)
            await notify(client_id, "image_gen", f"[{i}/{total}] Görsel üretiliyor: {sid}", pct)
            generate_scene_images(topic, [scene], style)
        await notify(client_id, "images_done", "Tüm görseller üretildi!", 100)
    except Exception as e:
        await notify(client_id, "error", str(e), -1)


class AIAnimateRequest(BaseModel):
    topic: str
    client_id: str = ""


@app.post("/api/ai/animate-images")
async def ai_animate_images(req: AIAnimateRequest, bg: BackgroundTasks):
    """Animate scene images using Hugging Face image-to-video."""
    if req.topic not in TOPICS:
        raise HTTPException(404, "Topic not found")
    bg.add_task(background_animate, req.topic, req.client_id)
    return {"status": "started", "topic": req.topic}


async def background_animate(topic: str, client_id: str):
    """Background task to animate images and notify via WebSocket."""
    try:
        from ai_generator import AI_IMG_DIR, AI_VID_DIR, animate_image
        topic_img_dir = AI_IMG_DIR / topic.replace(" ", "_").lower()
        if not topic_img_dir.exists():
            raise RuntimeError("No images found. Generate images first.")
        images_map = {p.stem: str(p) for p in topic_img_dir.glob("*.png")}
        total = len(images_map)
        for i, (sid, img_path) in enumerate(images_map.items(), 1):
            pct = int((i / total) * 100)
            await notify(client_id, "animating", f"[{i}/{total}] Resim hareketlendiriliyor: {sid}", pct)
            vid_path = AI_VID_DIR / topic.replace(" ", "_").lower() / f"{sid}.mp4"
            vid_path.parent.mkdir(parents=True, exist_ok=True)
            if not vid_path.exists():
                animate_image(img_path, str(vid_path))
        await notify(client_id, "animate_done", "Tüm resimler hareketlendirildi!", 100)
    except Exception as e:
        await notify(client_id, "error", str(e), -1)


@app.get("/api/ai/images/{topic}")
def get_ai_images(topic: str):
    """List AI-generated images for a topic."""
    from ai_generator import AI_IMG_DIR
    topic_dir = AI_IMG_DIR / topic.replace(" ", "_").lower()
    if not topic_dir.exists():
        return {"images": []}
    images = []
    for p in sorted(topic_dir.glob("*.png")):
        images.append({"scene_id": p.stem, "path": str(p), "name": p.name})
    return {"images": images}


@app.get("/api/ai/image/{topic}/{scene_id}")
def get_ai_image(topic: str, scene_id: str):
    """Serve a specific AI-generated image."""
    from ai_generator import AI_IMG_DIR
    path = AI_IMG_DIR / topic.replace(" ", "_").lower() / f"{scene_id}.png"
    if not path.exists():
        raise HTTPException(404, "Image not found")
    return FileResponse(str(path), media_type="image/png")


# Serve frontend static files (mount the frontend directory itself)
frontend_path = BASE / "web" / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

@app.get("/")
def root():
    index = BASE / "web" / "frontend" / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"status": "ok", "message": "YouTube Kids Studio API running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)