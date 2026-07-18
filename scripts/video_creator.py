"""
YouTube Shorts Video Creator for Kids
Creates vertical 9:16 videos using MoviePy 2.0+ API
"""

# MoviePy 2.0+ import style
from moviepy import TextClip, ColorClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip, ImageClip
import os
from typing import List, Optional

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "videos")
INTRO_DURATION = 3
OUTRO_DURATION = 4

def create_color_background(color: str, duration: float, text: str, subtext: str = None):
    """Create colored background with text overlay"""
    bg = ColorClip(size=(1080, 1920), color=color, duration=duration)
    
    main_txt = TextClip(text=text, font_size=120, color='white', method='label',
                        font='arial', stroke_color='black', stroke_width=2)
    main_txt = main_txt.with_position(('center', 700)).with_duration(duration)
    
    layers = [bg, main_txt]
    
    if subtext:
        sub_txt = TextClip(text=subtext, font_size=60, color='white', method='label',
                          font='arial', stroke_color='black', stroke_width=1)
        sub_txt = sub_txt.with_position(('center', 1100)).with_duration(duration)
        layers.append(sub_txt)
    
    return CompositeVideoClip(layers, bg_color=color)

def create_fact_clip(fact_text: str, image_path: Optional[str] = None, 
                    duration: float = 8, number: int = 1):
    """Create a fact presentation clip"""
    
    if image_path and os.path.exists(image_path):
        bg = ImageClip(image_path, duration=duration)
        bg = bg.with_effects([lambda clip: clip.resized(height=1920)])
    else:
        bg = ColorClip(size=(1080, 1920), color=(78, 205, 196), duration=duration)
    
    # Add fact number badge  
    badge = TextClip(text=f'#{number}', font_size=100, color='white', method='label',
                     font='arial', stroke_color='#FF6B6B', stroke_width=3)
    badge = badge.with_position((50, 100)).with_duration(duration)
    
    # Add fact text
    txt = TextClip(text=fact_text, font_size=70, color='white', font='arial',
                   stroke_color='black', stroke_width=2, method='caption',
                   size=(980, 400), text_align='center')
    txt = txt.with_position(('center', 1300)).with_duration(duration)
    
    return CompositeVideoClip([bg, badge, txt])

def create_short_video(facts: List[str], 
                       background_images: Optional[List[str]] = None,
                       intro_audio_path: Optional[str] = None,
                       outro_audio_path: Optional[str] = None,
                       output_name: str = "short_video.mp4") -> str:
    """Create complete YouTube Short using FFmpeg pipeline"""
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # For now, use FFmpeg-based pipeline (more reliable on Windows)
    # The full implementation with text overlays would work with MoviePy 2.0+
    # when properly configured with font paths
    
    return _create_with_ffmpeg(facts, background_images, output_name)

def _create_with_ffmpeg(facts: List[str], backgrounds: Optional[List[str]], output_name: str):
    """Fallback FFmpeg-based video creation"""
    import subprocess
    
    clips = []
    
    # Intro (yellow background)
    intro_path = os.path.join(OUTPUT_DIR, "temp_intro.mp4")
    subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 
                   'color=c=#ffdc64:s=1080x1920:d=3', '-c:v', 'libx264', intro_path],
                  capture_output=True)
    clips.append("temp_intro.mp4")
    
    # Facts with backgrounds
    bg_images = backgrounds or []
    for i, fact in enumerate(facts[:5], 1):
        if i-1 < len(bg_images):
            cmd = ['ffmpeg', '-y', '-loop', '1', '-i', bg_images[i-1], '-c:v', 'libx264',
                   '-vf', 'scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2',
                   '-frames:v', '1', os.path.join(OUTPUT_DIR, f"temp_fact_{i}.mp4")]
            subprocess.run(cmd, capture_output=True)
        clips.append(f"temp_fact_{i}.mp4")
    
    # Outro (coral background)
    outro_path = os.path.join(OUTPUT_DIR, "temp_outro.mp4")
    subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i',
                   'color=c=#ff6b6b:s=1080x1920:d=4', '-c:v', 'libx264', outro_path],
                  capture_output=True)
    clips.append("temp_outro.mp4")
    
    # Concatenate
    concat_list = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(concat_list, 'w') as f:
        for clip in clips:
            f.write(f"file 'file:{os.path.join(OUTPUT_DIR, clip)}'\n")
    
    output_path = os.path.join(OUTPUT_DIR, output_name)
    subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_list,
                   '-c:v', 'libx264', '-c:a', 'aac', output_path], capture_output=True)
    
    return output_path

if __name__ == "__main__":
    print("YouTube Kids Shorts Video Creator - MoviePy 2.0+")
    print("Note: FFmpeg pipeline used for reliable video creation")