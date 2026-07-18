# YouTube Kids Channel - Automated Video Creator

A complete toolkit for creating kid-friendly YouTube Shorts for English-speaking audiences (US/Canada/Australia).

## Features

- 🎬 **Automated Video Creation** - Creates vertical 9:16 Shorts
- 📷 **Pixabay Integration** - Royalty-free images & videos
- 🗣️ **Text-to-Speech** - Google TTS with child-friendly voices
- 🎨 **Custom Templates** - Intro/outro animations
- 📚 **Educational Content** - Facts about animals, space, geography, etc.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set Pixabay API key (get from https://pixabay.com/api/docs/)
echo "PIXABAY_API_KEY=your_api_key" > .env

# Run pipeline
python scripts/main_pipeline.py
```

## Project Structure

```
YouTube/
├── scripts/
│   ├── pixabay_downloader.py  # Media download from Pixabay
│   ├── voice_generator.py      # TTS voice generation
│   ├── video_creator.py        # MoviePy video assembly (requires v2.0+)
│   └── main_pipeline.py        # Main orchestration
├── output/
│   ├── videos/    # Generated Shorts
│   ├── audio/     # Voiceovers
│   └── images/    # Downloaded Pixabay images
├── content/
│   └── ideas/     # Content plan & templates
├── .env.example    # Environment template
└── requirements.txt
```

## Content Policy Compliance

✅ **100% Legal Content**
- All images/videos from Pixabay (CC0 license)
- Original script content
- No copyrighted material
- Kids-safe language and topics

## Target Audience

- 🇺🇸 United States
- 🇨🇦 Canada  
- 🇦🇺 Australia

## Video Specifications

- **Resolution**: 1080x1920 (9:16 vertical)
- **Max Duration**: 50 seconds
- **Format**: MP4 (H.264 + AAC)
- **Language**: English

## Requirements

- MoviePy 2.0+ (uses `from moviepy import *` syntax)
- FFmpeg (included with imageio)
- ImageMagick (optional, for text overlays)

## License

MIT License - Feel free to fork and customize!