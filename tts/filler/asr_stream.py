# asr_stream.py
import socket
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Optional

## 音声認識受け取る用のサーバー
@dataclass
class ASREvent:
    kind: str            
    text: str
    conf: Optional[float]
    ts: datetime

def iter_asr_events(host: str, port: int) -> Iterator[ASREvent]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    sock.settimeout(0.2)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    buf = ""
    last_conf: Optional[float] = None
    try:
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                continue

            if not chunk:
                return
            buf += chunk.decode("utf-8", errors="ignore")
            buf = buf.replace("\r\n", "\n").replace("\r", "\n")

            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                low = line.lower()
                if low.startswith("interimresult:"):
                    text = line.split(":", 1)[1].strip()
                    if text:
                        yield ASREvent("interim", text, last_conf, datetime.now())

                elif low.startswith("confidence:"):
                    try:
                        last_conf = float(line.split(":", 1)[1].strip())
                    except Exception:
                        last_conf = None

                elif low.startswith("result:"):
                    text = line.split(":", 1)[1].strip()
                    if text:
                        yield ASREvent("final", text, last_conf, datetime.now())
    finally:
        try:
            sock.close()
        except Exception:
            pass
