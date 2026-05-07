# xyz_server.py
import socket
import threading
from dataclasses import dataclass
from typing import Optional

SERVER_IP = "nikola-audiotracker"
SERVER_PORT = 7890
BUFFER_SIZE = 4096
N_FIELDS = 18

@dataclass
class XYZSample:
    timestamp: int
    act: int
    x: int
    y: int
    z: int
    humanId: int

def parse_numeric_line(line: bytes) -> Optional[list[int]]:
    try:
        s = line.decode("utf-8").strip()
    except UnicodeDecodeError:
        return None
    parts = s.split(",")
    if len(parts) != N_FIELDS:
        return None
    try:
        return [int(p) for p in parts]
    except ValueError:
        return None

class XYZClient:
    def __init__(self, host=SERVER_IP, port=SERVER_PORT):
        self.host = host
        self.port = port
        self._stop = threading.Event()
        self._th: Optional[threading.Thread] = None
        self.latest: Optional[XYZSample] = None
        self._lock = threading.Lock()
        self._last_valid_z = 1100

    def start(self):
        if self._th and self._th.is_alive():
            return
        self._stop.clear()
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()

    def stop(self):
        self._stop.set()

    def get_latest(self) -> Optional[XYZSample]:
        with self._lock:
            return self.latest

    def _run(self):
        buf = b""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.host, self.port))
                sock.settimeout(0.5)

                while not self._stop.is_set():
                    try:
                        chunk = sock.recv(BUFFER_SIZE)
                        if not chunk:
                            break
                        buf += chunk
                    except socket.timeout:
                        continue

                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        values = parse_numeric_line(line)
                        if values is None:
                            continue

                        # print(
                        #     f"[XYZ raw] timestamp={values[0]}, act={values[4]}, "
                        #     f"x={values[5]}, y={values[6]}, z={values[7]}, humanId={values[16]}"
                        # )
                        raw_z = values[7]

                        with self._lock:
                            if raw_z != -10000:
                                self._last_valid_z = raw_z

                        sample = XYZSample(
                            timestamp=values[0],
                            act = values[4],
                            x=values[5],
                            y=values[6],
                            z=self._last_valid_z,
                            humanId=values[16],
                        )
                        with self._lock:
                            self.latest = sample
        except Exception:
            # UIを止めないため握りつぶす（必要ならログ出しに変えてOK）
            pass
