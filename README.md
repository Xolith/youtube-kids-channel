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

# Run pipeline
python main_pipeline.py
```

## Project Structure

```
YouTube/
├── scripts/
│   ├── pixabay_downloader.py  # Media download from Pixabay
│   ├── voice_generator.py      # TTS voice generation
│   ├── video_creator.py        # MoviePy video assembly
│   └── main_pipeline.py        # Main orchestration
├── output/
│   ├── videos/    # Generated Shorts
│   ├── audio/     # Voiceovers
│   └── images/    # Downloaded Pixabay images
├── content/
│   └── ideas/     # Content plan & templates
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

## Pixabay API

Uses Pixabay API for royalty-free media:
- Key: `56396286-58d5762f4e09601e7c30b5cd7`
- Safe search enabled
- Kids-friendly content filters

## License

MIT License - Feel free to fork and customize!