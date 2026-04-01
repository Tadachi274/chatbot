# robot_client.py
import socket
import threading

## コマンドを送るようのサーバー
class RobotCommandClient:
    def __init__(self, host: str, port: int, eol: str = "lf", timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self._lock = threading.Lock()
        self._terminator = b"\n" if eol.lower() == "lf" else (b"\r\n" if eol.lower() == "crlf" else b"")

    def connect(self):
        with self._lock:
            if self.sock is not None:
                return
            self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            self.sock.settimeout(self.timeout)

    def close(self):
        with self._lock:
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
            self.sock = None

    def send(self, command: str):
        with self._lock:
            if self.sock is None:
                try:
                    self.connect()
                except Exception:
                    return
            try:
                self.sock.sendall(command.encode("utf-8") + self._terminator)
                print(f"[robot_client] {command.encode("utf-8")}")
            except (BrokenPipeError, ConnectionResetError):
                self.close()
                try:
                    self.connect()
                    self.sock.sendall(command.encode("utf-8") + self._terminator)
                    print(f"[robot_client] {command.encode("utf-8")}")
                except Exception as e:
                    print(f"[send_command] error{e}")
                    pass
            except Exception as e:
                print(f"[send_command] error{e}")
                pass
