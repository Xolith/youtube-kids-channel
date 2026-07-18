"""
Premium YouTube Kids Shorts Generator (B Plan - NO extra cost)
- AI images via FAL (image_generate tool) -> save to output/images/<topic>/
- Natural voice via OpenAI TTS (text_to_speech tool) -> save to output/audio/
- FFmpeg montage: Ken Burns zoom + animated subtitles + optional Pixabay music

Usage:
  python make_premium_video.py --topic space
"""

import os
import sys
import subprocess
import argparse
from pydub import AudioSegment

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(BASE, "output", "images")
AUD_DIR = os.path.join(BASE, "output", "audio")
VID_DIR = os.path.join(BASE, "output", "videos")
FONT = "/Windows/Fonts/arial.ttf"

# Content library: topic -> list of (filename_base, subtitle_text)
# Images & audio must be produced beforehand via image_generate / text_to_speech tools
CONTENT = {
    "space": {
        "scenes": [
            ("space_01_intro", "SPACE ADVENTURES"),
            ("space_02_fact1_sleep", "Astronauts sleep standing up!"),
            ("space_03_fact2_venus", "Venus is the hottest planet!"),
            ("space_04_fact3_stars", "More stars than sand!"),
            ("space_05_fact4_neptune", "Fastest winds in space!"),
            ("space_06_fact5_float", "You grow 5cm taller!"),
            ("space_07_outro", "SUBSCRIBE for more!"),
        ],
        "output": "space_adventures_premium.mp4",
    },
}


def build_scene(img_path, aud_path, subtitle, out_path, zoom_max=1.12):
    dur = AudioSegment.from_mp3(aud_path).duration_seconds + 0.3
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"zoompan=z='min(zoom+0.0008,{zoom_max})':d=1:"
        "x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920:fps=30,"
        f"drawtext=text='{subtitle}':fontcolor=white:fontsize=64:"
        f"fontfile={FONT}:box=1:boxcolor=black@0.5:boxborderw=20:"
        "x=(w-text_w)/2:y=h-180"
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", img_path, "-i", aud_path,
        "-vf", vf, "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
        "-t", str(dur), "-pix_fmt", "yuv420p", out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0


def add_music(video_path, music_path, out_path):
    """Mix background music under the voice track (music lowered to ~15%)."""
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-i", music_path,
        "-filter_complex",
        "[1:a]volume=0.15[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=0",
        "-c:v", "copy", "-c:a", "aac", out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="space")
    ap.add_argument("--music", default="", help="Optional background music mp3 (Pixabay)")
    args = ap.parse_args()

    if args.topic not in CONTENT:
        print("Unknown topic. Available:", list(CONTENT.keys()))
        return

    cfg = CONTENT[args.topic]
    clips = []
    for i, (base_name, sub) in enumerate(cfg["scenes"], 1):
        imgp = os.path.join(IMG_DIR, args.topic, f"{base_name}.png")
        audp = os.path.join(AUD_DIR, f"{base_name}.mp3")
        if not (os.path.exists(imgp) and os.path.exists(audp)):
            print(f"Missing assets for {base_name}, skipping: {imgp} / {audp}")
            continue
        out_clip = os.path.join(VID_DIR, f"{args.topic}_scene_{i:02d}.mp4")
        ok = build_scene(imgp, audp, sub, out_clip)
        print(f"Scene {i}: {'OK' if ok else 'FAILED'}")
        if ok:
            clips.append(out_clip)

    if not clips:
        print("No clips built.")
        return

    concat = os.path.join(VID_DIR, f"{args.topic}_concat.txt")
    with open(concat, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")

    final = os.path.join(VID_DIR, cfg["output"])
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", concat, "-c", "copy", final], capture_output=True)

    if args.music and os.path.exists(args.music):
        with_music = os.path.join(VID_DIR, "music_" + cfg["output"])
        if add_music(final, args.music, with_music):
            print("With music:", with_music)
        else:
            print("Music mix failed, plain video at:", final)
    else:
        print("Final video:", final)


if __name__ == "__main__":
    main()
