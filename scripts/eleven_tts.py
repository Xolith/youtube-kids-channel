"""
ElevenLabs TTS helper - child-friendly warm voice (Jessica by default)
Requires ELEVENLABS_API_KEY in .env or environment variable.
Free tier quota applies; no extra cost within limits.
"""

import os
import requests

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

def _load_key():
    key = os.getenv("ELEVENLABS_API_KEY")
    if key:
        return key
    try:
        txt = open(ENV_PATH).read()
        for line in txt.splitlines():
            if line.startswith("ELEVENLABS_API_KEY="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""

# Warm, playful child-friendly voice
DEFAULT_VOICE = "cgSgspJ2msm6clMCkdW9"  # Jessica - Playful, Bright, Warm


def tts(text: str, out_path: str, voice_id: str = DEFAULT_VOICE) -> str:
    """Generate speech via ElevenLabs and save to out_path."""
    key = _load_key()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY not found. Add it to .env")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
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
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(r.content)
    return out_path


if __name__ == "__main__":
    p = tts("Test from ElevenLabs helper.", "output/audio/_eleven_test.mp3")
    print("Saved:", p)
