# YouTube Kids Channel - Automated Video Creator

A complete toolkit for creating kid-friendly YouTube Shorts for English-speaking audiences (US/Canada/Australia).

## Features

- 🎬 **Automated Video Creation** - Creates vertical 9:16 Shorts
- 📷 **Pixabay Integration** - Royalty-free images & videos
- 🗣️ **ElevenLabs TTS** - Natural child-friendly voices (Jessica)
- 🤖 **FAL.ai Integration** - Free-tier image generation via Nous subscription
- 🎨 **Motion Graphics** - FFmpeg overlays (bubbles, rays, sparkles)
- 🌐 **Web Dashboard** - FastAPI backend + glassmorphism frontend

## Quick Start (Web App)

```bash
cd web/backend
pip install fastapi uvicorn==0.30.6 starlette==0.37.2 python-multipart pydantic

# Set environment (get ElevenLabs key from https://elevenlabs.io)
cp ../.env.example .env
echo "ELEVENLABS_API_KEY=your_api_key" >> .env

# Run
python main.py  # http://localhost:8001
```

### Web Dashboard
- Konu seç (Ocean Animals, Space Adventure)
- Stil seç (Cinematic 3D / Kawaii)
- PNG görseller yükle (9:16 vertical)
- Videoyu üret → WebSocket gerçek zamanlı ilerleme

## FAL Image Generation (Free-Tier)

**Nous aboneliği olmadan:**
- `image_generate` aracı FAL ücretsiz çalışır
- Görselleri agent arayüzünden üret → klasöre kaydet
- Web'den yükle → video üret

**API key ile:**
- `ai_generator.py` içinde `HF_TOKEN` veya `FAL_KEY` `.env`'ye ekleyin
- Backend `/api/generate-image` endpoint'ini tetikleyin

## Project Structure

```
YouTube/
├── web/
│   ├── backend/
│   │   ├── main.py       # FastAPI server + WebSocket
│   │   ├── pipeline.py   # Video assembly logic
│   │   └── ai_generator.py  # FAL/HF/OpenRouter hooks
│   └── frontend/
│       └── index.html    # Glassmorphism dashboard
├── scripts/                # Legacy MoviePy scripts (backup)
├── output/
│   ├── videos/    # Generated Shorts
│   ├── audio/     # Voiceovers  
│   └── images/    # Pixabay/AI-generated images
├── hunyuan/              # HunyuanVideo repo (reference)
├── .env.example          # Environment template
└── .gitignore            # .env + output/ ignored
```

## Content Policy Compliance

✅ **100% Legal Content**
- Pixabay (CC0 license) + AI-generated (FAL free-tier)
- ElevenLabs'den ücretsiz Jessica sesi
- Kids-safe language

## Target Audience
- 🇺🇸 United States
- 🇨🇦 Canada  
- 🇦🇺 Australia

## Video Specifications
- Format: MP4 (H.264)
- Resolution: 1080x1920 (9:16 vertical)
- Duration: 8-60 seconds (Shorts)
- Style: Pixar-quality 3D, rich detail