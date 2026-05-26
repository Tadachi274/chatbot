#!/usr/bin/env python3
import argparse
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import sys
import threading
import wave


CHATBOT_DIR = Path(__file__).resolve().parents[2]
if str(CHATBOT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR.parent))
if __package__ in (None, ""):
    __package__ = "chatbot.robot_style_editor.clients"

from ...tts import tts_nikola_data as tts
from ...tts.tts_audioplayer import AudioPlayer
from ..audio.wav_silence import trim_silence_to_wav


DEFAULT_TTS_URL = "http://127.0.0.1:15001/synthesize"


class NikolaTTSPlayHandler(BaseHTTPRequestHandler):
    server_version = "NikolaTTSPlayServer/0.1"

    def do_GET(self):
        if self.path in ("/", "/health"):
            self.send_json({"ok": True, "message": "ready"})
            return
        self.send_error(404, "not found")

    def do_POST(self):
        if self.path == "/speak":
            self.handle_speak()
            return
        if self.path == "/prepare":
            self.handle_prepare()
            return
        if self.path == "/play":
            self.handle_play()
            return

        self.send_error(404, "not found")

    def handle_speak(self):
        try:
            payload = self.read_json()
            text = str(payload.get("text", "")).strip()
            if not text:
                raise ValueError("text is empty")

            instructions = payload.get("instructions", {}) or {}
            person = payload.get("person") or tts.DEFAULT_PERSON
            tts_url = payload.get("tts_url") or self.server.tts_url

            print(
                f"[NikolaTTSPlayServer] speak text={text!r} "
                f"person={person} url={tts_url}",
                flush=True,
            )
            tts.speak_async(
                text=text,
                instructions=instructions,
                url=tts_url,
                person=person,
            )
            self.send_json({"ok": True})
        except Exception as e:
            print(f"[NikolaTTSPlayServer] speak error: {e}", flush=True)
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_prepare(self):
        try:
            payload = self.read_json()
            text = str(payload.get("text", "")).strip()
            if not text:
                raise ValueError("text is empty")

            instructions = payload.get("instructions", {}) or {}
            person = payload.get("person") or tts.DEFAULT_PERSON
            tts_url = payload.get("tts_url") or self.server.tts_url
            audio_id = self.audio_id_for(text, instructions, person, tts_url)

            print(
                f"[NikolaTTSPlayServer] prepare id={audio_id} text={text!r} "
                f"person={person} url={tts_url}",
                flush=True,
            )

            target = self.server.cache_dir / f"{audio_id}.wav"
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                wav_path = Path(
                    tts._synthesize_to_wav(
                        text=text,
                        instructions=instructions,
                        url=tts_url,
                        person=person,
                    )
                )
                try:
                    trim_silence_to_wav(wav_path, target)
                    wav_path.unlink(missing_ok=True)
                except Exception:
                    shutil.move(str(wav_path), str(target))

            duration = self.wav_duration_sec(target)
            with self.server.audio_lock:
                self.server.audio_registry[audio_id] = {
                    "path": target,
                    "duration": duration,
                    "text": text,
                    "person": person,
                }
            self.send_json({"ok": True, "audio_id": audio_id, "duration": duration})
        except Exception as e:
            print(f"[NikolaTTSPlayServer] prepare error: {e}", flush=True)
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def handle_play(self):
        try:
            payload = self.read_json()
            audio_id = str(payload.get("audio_id", "")).strip()
            wait = bool(payload.get("wait", True))
            timeout = float(payload.get("timeout", 60.0))
            if not audio_id:
                raise ValueError("audio_id is empty")

            with self.server.audio_lock:
                entry = self.server.audio_registry.get(audio_id)
            if not entry:
                raise FileNotFoundError(f"prepared audio not found: {audio_id}")

            wav_path = Path(entry["path"])
            if not wav_path.exists():
                raise FileNotFoundError(f"WAV file not found: {wav_path}")

            print(f"[NikolaTTSPlayServer] play id={audio_id} wait={wait}", flush=True)
            done = threading.Event() if wait else None
            self.server.audio_player.play_later(wav_path, done_event=done)
            if done is not None and not done.wait(timeout=timeout):
                self.server.audio_player.stop_current()
                raise TimeoutError(f"play timeout: {audio_id}")

            self.send_json({"ok": True, "audio_id": audio_id, "duration": entry.get("duration", 0.0)})
        except Exception as e:
            print(f"[NikolaTTSPlayServer] play error: {e}", flush=True)
            self.send_json({"ok": False, "error": str(e)}, status=500)

    def wav_duration_sec(self, wav_path):
        with wave.open(str(wav_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
        return frames / float(rate) if rate else 0.0

    def audio_id_for(self, text, instructions, person, tts_url):
        payload = {
            "text": text,
            "instructions": instructions,
            "person": person,
            "tts_url": tts_url,
            "cache_version": 1,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def send_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(
            f"[NikolaTTSPlayServer] {self.address_string()} - {fmt % args}",
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser(description="Receive TTS speak commands and play audio on Nikola PC.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=15003)
    parser.add_argument("--tts-url", default=DEFAULT_TTS_URL)
    parser.add_argument("--cache-dir", default=str(Path(__file__).resolve().parents[1] / "sample_audio" / "wav" / "nikola_remote_cache"))
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), NikolaTTSPlayHandler)
    server.tts_url = args.tts_url
    server.cache_dir = Path(args.cache_dir)
    server.cache_dir.mkdir(parents=True, exist_ok=True)
    server.audio_registry = {}
    server.audio_lock = threading.Lock()
    server.audio_player = AudioPlayer(autoremove=False)
    print(
        f"[NikolaTTSPlayServer] starting on http://{args.host}:{args.port} "
        f"default_tts_url={args.tts_url} cache_dir={server.cache_dir}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            server.audio_player.stop()
        except Exception:
            pass
        server.server_close()


if __name__ == "__main__":
    main()
