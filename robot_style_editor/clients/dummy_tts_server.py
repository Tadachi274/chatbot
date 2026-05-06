# chatbot/robot_style_editor/clients/dummy_tts_server.py

import argparse
import io
import json
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import wave


HOST = "127.0.0.1"
PORT = 15001
SAMPLE_RATE = 16000


def clamp(value, vmin, vmax):
    return max(vmin, min(value, vmax))


def make_dummy_wav(text, instructions):
    text = text.strip() or "dummy"
    rate = float(instructions.get("tts_rate", 1.0) or 1.0)
    pitch = float(instructions.get("tts_pitch", 1.0) or 1.0)
    volume = float(instructions.get("tts_volume", 1.0) or 1.0)
    joy = float(instructions.get("tts_emo_joy", 0.0) or 0.0)

    duration_sec = clamp((0.18 + len(text) * 0.055) / max(0.5, rate), 0.25, 6.0)
    frequency = clamp(440.0 * pitch + joy * 160.0, 180.0, 900.0)
    amplitude = int(clamp(volume / 2.0, 0.05, 0.95) * 16000)
    total_frames = int(SAMPLE_RATE * duration_sec)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)

        frames = bytearray()
        for index in range(total_frames):
            t = index / SAMPLE_RATE
            fade = min(1.0, index / max(1, int(SAMPLE_RATE * 0.03)))
            fade = min(fade, (total_frames - index) / max(1, int(SAMPLE_RATE * 0.04)))
            sample = int(amplitude * fade * math.sin(2 * math.pi * frequency * t))
            frames.extend(sample.to_bytes(2, byteorder="little", signed=True))

        wav.writeframes(bytes(frames))

    return buffer.getvalue(), duration_sec


class DummyTTSHandler(BaseHTTPRequestHandler):
    server_version = "DummyTTSServer/1.0"

    def do_GET(self):
        if self.path in ("/", "/health", "/synthesize"):
            body = b"ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_error(404, "not found")

    def do_POST(self):
        if self.path != "/synthesize":
            self.send_error(404, "not found")
            return

        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length)

        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self.send_error(400, "invalid json")
            return

        text = payload.get("text", "")
        wav_bytes, duration = make_dummy_wav(text, payload)

        print(
            "[DummyTTSServer] synthesize "
            f"text={text!r} duration={duration:.2f}s "
            f"rate={payload.get('tts_rate', 1.0)} pitch={payload.get('tts_pitch', 1.0)}"
        )

        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(wav_bytes)))
        self.end_headers()
        self.wfile.write(wav_bytes)

    def log_message(self, fmt, *args):
        print(f"[DummyTTSServer] {self.address_string()} - {fmt % args}")


def main():
    parser = argparse.ArgumentParser(description="Dummy TTS HTTP server for robot_style_editor.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), DummyTTSHandler)
    print(f"[DummyTTSServer] starting on http://{args.host}:{args.port}/synthesize")
    print("[DummyTTSServer] ready")
    server.serve_forever()


if __name__ == "__main__":
    main()
