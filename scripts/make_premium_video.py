"""
Premium YouTube Kids Shorts Generator - v2 (animated scenes, NO extra cost)

Pipeline per video:
  1. AI images  -> image_generate tool -> output/images/<topic>/*.png
  2. Natural TTS -> text_to_speech tool -> output/audio/<topic>_*.mp3
  3. FFmpeg montage:
       - zoompan (Ken Burns)
       - animated bubble/particle overlay layer (rising bubbles)
       - animated subtitle cards
       - optional Pixabay music mix

Usage:
  python make_premium_video.py --topic ocean [--music path/to/music.mp3]
"""

import os
import subprocess
import argparse
from pydub import AudioSegment
from PIL import Image, ImageDraw
import random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(BASE, "output", "images")
AUD_DIR = os.path.join(BASE, "output", "audio")
VID_DIR = os.path.join(BASE, "output", "videos")
FONT = "/Windows/Fonts/arial.ttf"

# topic -> ordered list of (image_base, audio_base, subtitle, bubbles?)
CONTENT = {
    "ocean": {
        "output": "ocean_animals_premium.mp4",
        "scenes": [
            ("01_intro",        "ocean_01_intro",   "OCEAN ADVENTURE",       True),
            ("02_fact1_octopus","ocean_02_fact1_octopus","Octopus = 3 hearts!", False),
            ("03_fact2_dolphin","ocean_03_fact2_dolphin","Dolphins have names!", True),
            ("04_fact3_starfish","ocean_04_fact3_starfish","Starfish regrows!", False),
            ("05_fact4_seahorse","ocean_05_fact4_seahorse","Daddy carries babies!", True),
            ("06_fact5_whale",  "ocean_06_fact5_whale","Biggest heart ever!",  False),
            ("07_outro",        "ocean_07_outro",   "SUBSCRIBE under the sea!", True),
        ],
    },
}


def make_bubble_layer(path, count=40, frames=300):
    """Create a looping transparent bubble overlay video (rising bubbles)."""
    png = os.path.join(VID_DIR, "fx_bubble.png")
    im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    random.seed(7)
    for _ in range(count):
        x = random.randint(20, 1060); y = random.randint(20, 1900)
        r = random.randint(6, 18)
        d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 255, 70), width=3)
    im.save(png)
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", png, "-frames:v", str(frames),
        "-vf", "format=rgba,split[a][b];[b]crop=1080:1920:0:0[a2];"
               "[a][a2]overlay=y='-mod(t*60,1920)'",
        "-c:v", "png", path,
    ]
    subprocess.run(cmd, capture_output=True)
    return path


def dur_of(mp3):
    try:
        return AudioSegment.from_mp3(mp3).duration_seconds + 0.4
    except Exception:
        return 4.0


def build_scene(img_path, aud_path, subtitle, out_path, zoom=1.06, bubbles=False, bubble_layer=None):
    d = dur_of(aud_path)
    base = (
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"zoompan=z='min(zoom+0.0006,{zoom})':d=1:"
        "x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920:fps=30"
    )
    sub = (
        f"drawtext=text='{subtitle}':fontcolor=white:fontsize=62:fontfile={FONT}:"
        "box=1:boxcolor=black@0.45:boxborderw=18:x=(w-text_w)/2:y=h-170"
    )
    if bubbles and bubble_layer:
        filt = f"[0:v]{base}[bg];[1:v]format=rgba[f];[bg][f]overlay=shortest=1,{sub}"
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-i", bubble_layer,
               "-i", aud_path, "-filter_complex", filt, "-t", str(d),
               "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", out_path]
    else:
        vf = base + "," + sub
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-i", aud_path, "-vf", vf,
               "-t", str(d), "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
               "-pix_fmt", "yuv420p", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0


def add_music(video_path, music_path, out_path):
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-i", music_path,
        "-filter_complex",
        "[1:a]volume=0.15[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=0",
        "-c:v", "copy", "-c:a", "aac", out_path,
    ]
    return subprocess.run(cmd, capture_output=True).returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="ocean")
    ap.add_argument("--music", default="")
    args = ap.parse_args()

    if args.topic not in CONTENT:
        print("Available:", list(CONTENT.keys()))
        return

    cfg = CONTENT[args.topic]
    os.makedirs(VID_DIR, exist_ok=True)
    bubble_layer = os.path.join(VID_DIR, "fx_bubbles.mp4")
    make_bubble_layer(bubble_layer)

    clips = []
    for i, (im, au, sub, bub) in enumerate(cfg["scenes"], 1):
        ip = os.path.join(IMG_DIR, args.topic, f"{im}.png")
        ap_ = os.path.join(AUD_DIR, f"{au}.mp3")
        op = os.path.join(VID_DIR, f"{args.topic}_{i:02d}.mp4")
        if not (os.path.exists(ip) and os.path.exists(ap_)):
            print("Missing", ip, ap_); continue
        ok = build_scene(ip, ap_, sub, op, bubbles=bub, bubble_layer=bubble_layer)
        print(f"Scene {i}: {'OK' if ok else 'FAIL'}")
        if ok:
            clips.append(op)

    ct = os.path.join(VID_DIR, f"{args.topic}_concat.txt")
    with open(ct, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    final = os.path.join(VID_DIR, cfg["output"])
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", ct,
                    "-c", "copy", final], capture_output=True)

    if args.music and os.path.exists(args.music):
        wm = os.path.join(VID_DIR, "music_" + cfg["output"])
        if add_music(final, args.music, wm):
            print("With music:", wm)
    else:
        print("Final:", final)


if __name__ == "__main__":
    main()
