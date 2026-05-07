import hashlib
import json
from pathlib import Path
import shutil
import threading

from ..config import STYLE_SAMPLE_TTS_CACHE_DIR


_CACHE_LOCKS = {}
_CACHE_LOCKS_GUARD = threading.Lock()


class StyleSampleAudioMixin:
    def style_sample_person(self):
        return self.profile_store.get("speaker", None)

    def style_sample_cache_path(self, text, person):
        payload = {
            "text": text,
            "person": person or "",
            "cache_version": 1,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
        safe_text = "".join("_" if char in '\\/:*?"<>| \t\r\n' else char for char in text).strip("_")
        safe_text = safe_text[:28] or "style_sample"
        return STYLE_SAMPLE_TTS_CACHE_DIR / f"{digest}_{safe_text}.wav"

    def get_or_create_style_sample_wav(self, text):
        text = (text or "").strip()
        if not text:
            return None, False

        person = self.style_sample_person()
        cache_path = self.style_sample_cache_path(text, person)
        if cache_path.exists():
            return cache_path, True

        with _CACHE_LOCKS_GUARD:
            lock = _CACHE_LOCKS.setdefault(str(cache_path), threading.Lock())

        with lock:
            if cache_path.exists():
                return cache_path, True

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            wav_path = self.tts_client.synthesize_to_wav(
                text=text,
                person=person,
            )
            if wav_path is None:
                return None, False

            wav_path = Path(wav_path)
            try:
                shutil.move(str(wav_path), str(cache_path))
            except Exception:
                shutil.copy2(str(wav_path), str(cache_path))
                try:
                    wav_path.unlink(missing_ok=True)
                except Exception:
                    pass
            return cache_path, False

    def play_style_sample_text(self, text, label="スタイル例文"):
        text = (text or "").strip()
        if not text:
            return

        def worker():
            try:
                wav_path, cache_hit = self.get_or_create_style_sample_wav(text)
                if wav_path is None:
                    return
                self.tts_client.play_preview_wav(wav_path)
                action = "再生" if cache_hit else "生成して再生"
                self.status_var.set(f"{label}を{action}しました: {text}")
            except Exception as e:
                self.status_var.set(f"{label}の再生エラー: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def prewarm_style_sample_wavs(self, options):
        texts = []
        for opt in options:
            if opt.get("id") == "other":
                continue
            for key in ("example1", "example2"):
                text = (opt.get(key) or "").strip()
                if text:
                    texts.append(text)

        if not texts:
            return

        unique_texts = list(dict.fromkeys(texts))

        def worker():
            for text in unique_texts:
                try:
                    self.get_or_create_style_sample_wav(text)
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()
