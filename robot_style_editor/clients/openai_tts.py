import json
import os
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ..config import TTS_GENERATED_WAV_DIR


OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech"
DEFAULT_OPENAI_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_OPENAI_TTS_VOICE = "marin"


def synthesize_to_wav(
    text: str,
    instructions: dict | None = None,
    output_dir: Path | None = TTS_GENERATED_WAV_DIR,
) -> Path:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が設定されていません")

    text = text.strip()
    if not text:
        raise ValueError("text is empty")

    output_dir = Path(output_dir or TTS_GENERATED_WAV_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    wav_path = output_dir / make_filename(text)

    payload = {
        "model": os.environ.get("OPENAI_TTS_MODEL", DEFAULT_OPENAI_TTS_MODEL),
        "voice": os.environ.get("OPENAI_TTS_VOICE", DEFAULT_OPENAI_TTS_VOICE),
        "input": text,
        "response_format": "wav",
    }
    prompt = openai_voice_prompt(instructions or {})
    if prompt:
        payload["instructions"] = prompt

    req = urllib.request.Request(
        OPENAI_SPEECH_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            wav_path.write_bytes(res.read())
    except Exception as exc:
        raise RuntimeError(f"OpenAI TTS生成に失敗しました: {exc}") from exc

    return wav_path


def openai_voice_prompt(instructions: dict):
    parts = ["Speak naturally in English."]

    rate = safe_float(instructions.get("tts_rate"), 1.0)
    pitch = safe_float(instructions.get("tts_pitch"), 1.0)
    joy = safe_float(instructions.get("tts_emo_joy"), 0.0)
    anger = safe_float(instructions.get("tts_emo_angry"), 0.0)
    sadness = safe_float(instructions.get("tts_emo_sad"), 0.0)
    emphasis = safe_float(instructions.get("tts_emphasis"), 1.0)

    if rate <= 0.85:
        parts.append("Use a slower speaking pace.")
    elif rate >= 1.15:
        parts.append("Use a faster speaking pace.")

    if pitch <= 0.9:
        parts.append("Use a slightly lower, calmer voice.")
    elif pitch >= 1.1:
        parts.append("Use a slightly brighter voice.")

    if sadness >= 0.6:
        parts.append("Sound apologetic and a little sad.")
    if joy >= 0.6:
        parts.append("Sound warm and friendly.")
    if anger >= 0.6:
        parts.append("Sound firm, but still polite.")
    if emphasis >= 1.15:
        parts.append("Make the intonation a little more expressive.")
    elif emphasis <= 0.85:
        parts.append("Keep the intonation restrained.")

    return " ".join(parts)


def safe_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def make_filename(text):
    safe_text = re.sub(r"[\\/:*?\"<>|\s]+", "_", text).strip("_")
    safe_text = safe_text[:32] or "openai_tts"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}_{uuid4().hex[:8]}_openai_{safe_text}.wav"
