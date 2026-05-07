import socket
import threading

from ..config import (
    ROBOT_TCP_HOST,
    ROBOT_TCP_PORT,
    ROBOT_TCP_EOL,
    ROBOT_TCP_TIMEOUT,
)

try:
    from chatbot.tts.command.command import send_command as send_single_command
except Exception:
    send_single_command = None


class RobotCommandClient:
    """
    robot_style_editor からロボットコマンドを送るための窓口。

    UI側はこのクラスだけを使う。
    内部送信は、
      - persistent=True: socketを保持して連続送信
      - persistent=False: command.py の send_command で単発送信
    を選べる。
    """

    def __init__(
        self,
        host: str = ROBOT_TCP_HOST,
        port: int = ROBOT_TCP_PORT,
        timeout: float = ROBOT_TCP_TIMEOUT,
        eol: str = ROBOT_TCP_EOL,
        persistent: bool = True,
        receive: bool = False,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.eol = eol
        self.persistent = persistent
        self.receive = receive

        self.sock = None
        self._lock = threading.Lock()
        self.terminator = self._eol_bytes(eol)

    def _eol_bytes(self, eol: str) -> bytes:
        eol = eol.lower()
        if eol == "crlf":
            return b"\r\n"
        if eol == "none":
            return b""
        return b"\n"

    def connect(self):
        if self.sock is not None:
            return

        self.sock = socket.create_connection(
            (self.host, self.port),
            timeout=self.timeout,
        )
        self.sock.settimeout(self.timeout)

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def send(self, command: str):
        print(f"[RobotCommandClient] > {command}")

        try:
            if self.persistent:
                self._send_persistent(command)
            else:
                self._send_single(command)
        except Exception as e:
            print(f"[RobotCommandClient] send error: {e}")

    def _send_persistent(self, command: str):
        with self._lock:
            try:
                if self.sock is None:
                    self.connect()

                self.sock.sendall(command.encode("utf-8") + self.terminator)
                return

            except (BrokenPipeError, ConnectionResetError, OSError):
                self.close()

            try:
                self.connect()
                self.sock.sendall(command.encode("utf-8") + self.terminator)
            except Exception as e:
                self.close()
                print(f"[RobotCommandClient] persistent send failed: {e}")

    def _send_single(self, command: str):
        if send_single_command is None:
            raise ImportError(
                "chatbot.tts.command.command.send_command を import できません。"
                "__init__.py と実行パスを確認してください。"
            )

        return send_single_command(
            host=self.host,
            port=self.port,
            command=command,
            timeout=self.timeout,
            eol=self.eol,
            receive=self.receive,
        )

    def send_emotion(self, face_type: str, level: int, priority: int, keeptime: int):
        self.send(f"/emotion {face_type} {level} {priority} {keeptime}")

    def send_lookaway(self, direction: str, priority: int, keeptime: int):
        self.send(f"/lookaway {direction} {priority} {keeptime}")

    def send_face_axis(self, axis: str, value: int, velocity: int, priority: int, keeptime: int):
        self.send(f"/movemulti5 {axis} {value} {velocity} {priority} {keeptime}")

    def send_nod(self, amplitude: int, duration: int, times: int, priority: int):
        self.send(f"/nod {amplitude} {duration} {times} {priority}")

    def send_face_axes(self, axes: dict[str, int], velocity: int, priority: int, keeptime: int):
        for axis, value in axes.items():
            self.send_face_axis(
                axis=axis,
                value=int(value),
                velocity=velocity,
                priority=priority,
                keeptime=keeptime,
            )
