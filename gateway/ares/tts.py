"""ElevenLabs text-to-speech for the audit-log assistant.

Returns MP3 bytes when ELEVENLABS_API_KEY is set and the call succeeds; otherwise None,
so the frontend degrades to text-only. The key never reaches the browser: the frontend
posts text here and the gateway calls ElevenLabs server-side.
"""
from __future__ import annotations

import json
import os
import urllib.request

# Default voice "Roger" — a clear voice usable on the ElevenLabs free API tier. Override with
# ELEVENLABS_VOICE_ID if you pick another from the ElevenLabs voice library.
DEFAULT_VOICE = "CwhRBWXzGAHq8TQ4Fs17"  # Roger — usable on the ElevenLabs free API tier
ELEVEN_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_turbo_v2_5")


def available() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


def synthesize(text: str) -> bytes | None:
    """Turn text into MP3 audio bytes via ElevenLabs. None if unavailable or on failure."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key or not text.strip():
        return None
    voice = os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE)
    url = (f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
           f"?output_format=mp3_44100_128")
    body = {
        "text": text,
        "model_id": os.environ.get("ELEVENLABS_MODEL", ELEVEN_MODEL),
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "xi-api-key": key,
            "Accept": "audio/mpeg",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read()
    except Exception as exc:
        print(f"[tts] elevenlabs unavailable: {exc!r}", flush=True)
        return None
