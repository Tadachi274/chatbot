# launcher.py
import subprocess
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

WATCH_DIR = Path(__file__).parent  # 監視するディレクトリ
PY_CMD = [sys.executable, str(WATCH_DIR / "robot_console.py")]  # 実行するtkアプリ

class RestartHandler(FileSystemEventHandler):
    def __init__(self, restart_callback, patterns=(".py",)):
        self.restart_callback = restart_callback
        self.patterns = patterns

    def on_any_event(self, event):
        # ファイルの作成/変更/削除で再起動（短絡的に）
        if any(str(event.src_path).endswith(p) for p in self.patterns):
            print("Detected change:", event.src_path)
            self.restart_callback()

def main():
    proc = None
    def start_proc():
        nonlocal proc
        if proc and proc.poll() is None:
            return
        print("Starting app...")
        proc = subprocess.Popen(PY_CMD)
    def restart_proc():
        nonlocal proc
        print("Restarting app...")
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
        start_proc()

    start_proc()

    observer = Observer()
    handler = RestartHandler(restart_proc)
    observer.schedule(handler, str(WATCH_DIR), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(0.5)
            # optional: auto-restart if child died
            if proc and proc.poll() is not None:
                print("App exited; restarting...")
                start_proc()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        observer.stop()
        observer.join()
        if proc and proc.poll() is None:
            proc.terminate()
            proc.wait()

if __name__ == "__main__":
    main()