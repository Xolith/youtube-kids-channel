"""
YouTube Shorts Video Creator for Kids
Creates vertical 9:16 videos with MoviePy + Pixabay + TTS
"""

from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    ColorClip, concatenate_videoclips
)
from moviepy.video.fx.all import fadein, fadeout
import os
from typing import List, Optional, Tuple

BASE_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "output", "videos")
INTRO_DURATION = 3  # seconds
OUTRO_DURATION = 4  # seconds
SHORT_DURATION = 50  # seconds max for Shorts

# Kids-friendly fonts and colors
FONTS = {
    "main": "Arial-Bold",  # Fallback to system Arial
    "subtitle": "Arial"
}

COLORS = {
    "primary": "#FF6B6B",    # Coral red (friendly)
    "secondary": "#4ECDC4",  # Turquoise
    "background": "#FFE66D", # Yellow
    "text": "#FFFFFF",
    "accent": "#95E1D3"
}

def create_intro(duration: int = 3) -> ColorClip:
    """Create channel intro with animated text"""
    # Create background clip
    intro = ColorClip(
        size=(1080, 1920),
        color=(255, 220, 100),  # Warm yellow
        duration=duration
    )
    
    # Add text
    text = TextClip(
        "Kids Fun Facts!",
        fontsize=120,
        font=FONTS["main"],
        color=COLORS["primary"],
        method="caption",
        size=(1080, 400),
        align="center"
    ).set_position(("center", 700)).set_duration(duration)
    
    # Add subtitle
    subtitle = TextClip(
        "Learn something amazing!",
        fontsize=60,
        font=FONTS["subtitle"],
        color=COLORS["text"],
        method="caption",
        size=(1080, 200),
        align="center"
    ).set_position(("center", 1100)).set_duration(duration)
    
    return CompositeVideoClip([intro, text, subtitle])

def create_fact_clip(fact_text: str, image_path: Optional[str] = None, 
                    duration: int = 8, number: int = 1) -> CompositeVideoClip:
    """Create a fact presentation clip"""
    
    if image_path and os.path.exists(image_path):
        clip = VideoFileClip(image_path).resize(height=1920)
        # Make image same duration as text
        clip = clip.set_duration(duration)
        # Crop to 1080x1920 (9:16)
        w, h = clip.size
        if w > 1080:
            clip = clip.crop(x_center=w/2, y_center=h/2, width=1080, height=1920)
    else:
        # Fallback color background
        clip = ColorClip(
            size=(1080, 1920),
            color=(78, 205, 196),  # Turquoise
            duration=duration
        )
    
    # Add fact number badge
    badge = TextClip(
        f"#{number}",
        fontsize=100,
        font=FONTS["main"],
        color="white",
        stroke_color=COLORS["primary"],
        stroke_width=3,
        method="label"
    ).set_position((50, 100)).set_duration(duration)
    
    # Add fact text
    txt = TextClip(
        fact_text,
        fontsize=70,
        font=FONTS["subtitle"],
        color="white",
        stroke_color="black",
        stroke_width=2,
        method="caption",
        size=(980, 600),
        align="center"
    ).set_position(("center", 1300)).set_duration(duration)
    
    return CompositeVideoClip([clip, badge, txt])

def create_outro(duration: int = 4) -> ColorClip:
    """Create video outro with subscribe prompt"""
    outro = ColorClip(
        size=(1080, 1920),
        color=(255, 107, 107),  # Coral
        duration=duration
    )
    
    text = TextClip(
        "Subscribe for more fun!",
        fontsize=90,
        font=FONTS["main"],
        color="white",
        method="caption",
        size=(1080, 400),
        align="center"
    ).set_position(("center", 700)).set_duration(duration)
    
    emoji = TextClip(
        "👋 🎉 ✨",
        fontsize=120,
        font="Arial",
        color="white",
        method="label"
    ).set_position(("center", 1200)).set_duration(duration)
    
    return CompositeVideoClip([outro, text, emoji])

def create_short_video(facts: List[str], 
                       background_videos: Optional[List[str]] = None,
                       intro_audio: Optional[str] = None,
                       outro_audio: Optional[str] = None,
                       output_name: str = "short_video.mp4") -> str:
    """Create complete YouTube Short"""
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    clips = []
    
    # Add intro
    intro = create_intro(INTRO_DURATION)
    if intro_audio and os.path.exists(intro_audio):
        audio = AudioFileClip(intro_audio).set_duration(INTRO_DURATION)
        intro = intro.set_audio(audio)
    clips.append(intro)
    
    # Add fact clips
    for i, fact in enumerate(facts[:5], 1):  # Max 5 facts for Shorts
        bg_video = background_videos[i-1] if background_videos and i-1 < len(background_videos) else None
        fact_clip = create_fact_clip(fact, bg_video, duration=8, number=i)
        clips.append(fact_clip)
    
    # Add outro
    outro = create_outro(OUTRO_DURATION)
    if outro_audio and os.path.exists(outro_audio):
        audio = AudioFileClip(outro_audio).set_duration(OUTRO_DURATION)
        outro = outro.set_audio(audio)
    clips.append(outro)
    
    # Concatenate all clips
    final_video = concatenate_videoclips(clips, method="compose")
    
    # Export
    output_path = os.path.join(OUTPUT_DIR, output_name)
    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
        threads=4,
        preset="medium"
    )
    
    return output_path

# Example usage
if __name__ == "__main__":
    # Test with sample facts
    sample_facts = [
        "Dolphins sleep with one eye open!",
        "Honey never spoils - archaeologists found 3000 year old honey!",
        "Octopuses have 3 hearts!",
        "Bananas grow on plants called 'herbs'!",
        "Sea otters hold hands while sleeping!"
    ]
    
    print("Creating sample short video...")
    print("Note: Run 'pip install -r requirements.txt' first!")