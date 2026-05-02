# chatbot/robot_style_editor/launcher.py

import subprocess
import sys
import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# launcher.py がある場所
EDITOR_DIR = Path(__file__).resolve().parent

# chatbot の親ディレクトリ
# /Users/stela/ryoji/chatbot/robot_style_editor/launcher.py
# parents[2] => /Users/stela/ryoji
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# python -m chatbot.robot_style_editor.main で起動
PY_CMD = [
    sys.executable,
    "-m",
    "chatbot.robot_style_editor.main",
]


class RestartHandler(FileSystemEventHandler):
    def __init__(self, restart_callback, patterns=(".py",), debounce_sec=0.4):
        self.restart_callback = restart_callback
        self.patterns = patterns
        self.debounce_sec = debounce_sec
        self.last_restart_time = 0.0

    def on_any_event(self, event):
        if event.is_directory:
            return

        path = str(event.src_path)

        # __pycache__ などは無視
        if "__pycache__" in path:
            return

        # .py 以外は無視
        if not any(path.endswith(p) for p in self.patterns):
            return

        now = time.time()

        # 保存時に複数イベントが飛ぶので、短時間の連続再起動を防ぐ
        if now - self.last_restart_time < self.debounce_sec:
            return

        self.last_restart_time = now

        print(f"[launcher] Detected change: {path}")
        self.restart_callback()


def main():
    proc = None

    def start_proc():
        nonlocal proc

        if proc and proc.poll() is None:
            return

        print("[launcher] Starting robot_style_editor...")

        proc = subprocess.Popen(
            PY_CMD,
            cwd=str(PROJECT_ROOT),
        )

    def restart_proc():
        nonlocal proc

        print("[launcher] Restarting robot_style_editor...")

        if proc and proc.poll() is None:
            proc.terminate()

            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

        start_proc()

    start_proc()

    observer = Observer()
    handler = RestartHandler(restart_proc)

    # robot_style_editor 配下だけ監視
    observer.schedule(
        handler,
        str(EDITOR_DIR),
        recursive=True,
    )

    observer.start()

    try:
        while True:
            time.sleep(1.0)

            # アプリが落ちたら自動再起動
            if proc and proc.poll() is not None:
                print("[launcher] App exited; restarting...")
                start_proc()

    except KeyboardInterrupt:
        print("[launcher] Stopping...")

    finally:
        observer.stop()
        observer.join()

        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


if __name__ == "__main__":
    main()