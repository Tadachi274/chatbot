import subprocess
import tempfile
from pathlib import Path

import pygame


class SpeedAudioPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.current_temp_path = None

    def make_speed_wav(self, src_path: Path, speed: float) -> Path:
        src_path = Path(src_path)

        if not src_path.exists():
            raise FileNotFoundError(f"WAV file not found: {src_path}")

        speed = max(0.5, min(2.0, float(speed)))

        temp = tempfile.NamedTemporaryFile(
            suffix=f"_speed_{speed:.2f}.wav",
            delete=False,
        )
        temp_path = Path(temp.name)
        temp.close()

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(src_path),
            "-filter:a", f"atempo={speed}",
            "-vn",
            str(temp_path),
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "ffmpeg failed:\n"
                + result.stderr
            )

        return temp_path

    def play(self, src_path: Path, speed: float):
        self.stop()

        temp_path = self.make_speed_wav(src_path, speed)
        self.current_temp_path = temp_path

        pygame.mixer.music.load(str(temp_path))
        pygame.mixer.music.play()

    def stop(self):
        try:
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except pygame.error:
                pass
        except Exception:
            pass

        if self.current_temp_path is not None:
            try:
                self.current_temp_path.unlink(missing_ok=True)
            except Exception:
                pass
            self.current_temp_path = None

    def cleanup(self):
        self.stop()