#!/usr/bin/env python3
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys


CHATBOT_DIR = Path(__file__).resolve().parents[2]
if str(CHATBOT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR.parent))

from chatbot.tts import tts_nikola_data as tts


DEFAULT_TTS_URL = "http://127.0.0.1:15001/synthesize"


class NikolaTTSPlayHandler(BaseHTTPRequestHandler):
    server_version = "NikolaTTSPlayServer/0.1"

    def do_GET(self):
        if self.path in ("/", "/health"):
            self.send_json({"ok": True, "message": "ready"})
            return
        self.send_error(404, "not found")

    def do_POST(self):
        if self.path != "/speak":
            self.send_error(404, "not found")
            return

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
            print(f"[NikolaTTSPlayServer] error: {e}", flush=True)
            self.send_json({"ok": False, "error": str(e)}, status=500)

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
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), NikolaTTSPlayHandler)
    server.tts_url = args.tts_url
    print(
        f"[NikolaTTSPlayServer] starting on http://{args.host}:{args.port}/speak "
        f"default_tts_url={args.tts_url}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
