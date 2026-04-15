#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import datetime
import random
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from urllib import request, error
import socket  # 追加
import requests
import simpleaudio as sa
import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import tts_nikola_data as tts
from tts_audioplayer import AudioPlayer
from xyz_server import XYZClient
import time


# ====== 設定 ======
COMMAND_ENDPOINT = "http://192.168.0.10:8000/cmd"   
# TCP接続設定（command.py類似仕様）
USE_TCP = True             # TrueでTCP常時接続モードを使用（HTTP送信は無効化）
TCP_HOST = "nikola-humantracker"
TCP_PORT = 8078
TCP_EOL  = "lf"              # lf / crlf / none
TCP_TIMEOUT = 5.0
# TTS_URL
TTS_URL = 'http://192.168.0.169:15001/synthesize'
VOICE_STATE_PATH = Path(__file__).with_name('voice_state.json')
FILLER_FACE_STATE_PATH = (Path(__file__).resolve().parents[1]       
    / "filler"
    / "filler_face_state.json"
)
FILLER_VOICE_STATE_PATH = (Path(__file__).resolve().parents[1]       
    / "filler"
    / "filler_voice_state.json"
)
SPEAKING_STYLE_STATE_PATH = Path(__file__).with_name("speaking_style_state.json")
VOICE_STATE_EMO_PATH = Path(__file__).with_name("voice_state_emo.json")
MOTION_STATE_PATH = Path(__file__).with_name("motion_state.json")
# =================

FRIENDLY_MAP = {
    "volume":   (1.3, 1.3),
    "rate":     (1.0, 1.0),
    "pitch":    (1.0, 1.05),
    "emphasis": (1.0, 1.05),
    "joy":      (0.0, 0.3),
    "anger":    (0.0, 0.0),
    "sadness":  (0.0, 0.3),
}

TRUST_MAP = {
    "volume":   (1.3, 1.3),
    "rate":     (1.0, 0.9),
    "pitch":    (1.0, 0.9),
    "emphasis": (1.0, 0.95),
    "joy":      (0.0, 0.0),
    "anger":    (0.0, 0.0),
    "sadness":  (0.0, 0.4),
}

TENSION_MAP = {
    "volume":   (1.3, 1.5),
    "rate":     (1.0, 1.2),
    "pitch":    (1.0, 1.2),
    "emphasis": (1.0, 1.3),
    "joy":      (0.0, 0.4),
    "anger":    (0.0, 0.0),
    "sadness":  (0.0, 0.1),
}

VOICE_RANGE = {
    "volume":   (0.0, 2.0),
    "rate":     (0.5, 4.0),
    "pitch":    (0.5, 2.0),
    "emphasis": (0.0, 2.0),
    "joy":      (0.0, 1.0),
    "anger":    (0.0, 1.0),
    "sadness":  (0.0, 1.0),
}

SMILES = [
    "AffiliativeSmile", 
    "RewardSmile", 
    "WaitSmile", 
    "AffiliativeSmileOpenEyes", 
    "WaitSmileOpenEyes"
] 

PERSON = [
    "nozomi_emo_22_standard",
    "kenta_emo_22_standard",
    "maki_emo_22_standard",
    "shiori_emo_22_standard",
    # "yamato_22_kansai",
    # "miyabi_22_kansai",
]

NOD_AMPLITUDES = {
            "small": 7,
            "mid": 10,
            "large": 15,
        }

GAZE_DIRS = [
            ("up-left","lu"), ("up","u"), ("up-right","ru"),
            ("left","l"), ("center","f"), ("right","r"),
            ("down-left","ld"), ("down","d"), ("down-right","rd"),
        ]

FILLER_EMOTIONS = [
    "Suspicion",
    "sorry",
    "Sad",
    "AffiliativeSmileOpenEyes",
    "WaitSmile",
    "WaitSmileOpenEyes",
    "AffiliativeSmile",
    "RewardSmile",
    "neutral",
]

CANT_HEAR_VOICE =[
    "すみません。もう一度よろしいでしょうか？",
    "なんて言ったの？",
    "んーー？",
    "んー？"
    "もう一回言って",
]

FILLER_CANDIDATES = [
    "ん",
    "はい",
    "ええ",
    "えっと",
    "あの",
    "ああ",
    "えっとー",
    "そうですね",
    "そうですねー",
    "そうなんですね",
    "そうなんですねー",
    "なるほど",
    "ちょっとまってくださいね",
    "少々お待ちください",
    "承知いたしました",
]

DEFAULT_SELECTED_FILLERS = {
    "ん",
    "はい",
    "ええ",
    "えっと",
    "あの",
}

class RobotConsole(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ロボット操作コンソール (Python)")
        self.geometry("2200x1200")

        # ---- 状態（既定値）----
        self.default_keeptime = tk.IntVar(value=1000) 
        self.smile_flag = tk.BooleanVar(value=False)
        self.laugh_flag = tk.BooleanVar(value=False)

        self.smile_level = tk.IntVar(value=1)    # 1-3
        self.smile_priority = tk.IntVar(value=1) 

        self.facial_emotions = [
            "TadachiSmile", "AffiliativeSmile", "RewardSmile"
        ]
        self.emotion_buttons = {}
        
        self.facial_emotion = tk.StringVar(value="TadachiSmile")
        self.emotion_level = tk.IntVar(value=1)
        self.emotion_priority = tk.IntVar(value=1)
        self.emotion_flag = tk.BooleanVar(value=False)

        self.volume   = tk.DoubleVar(value=1.3)  # 0.0-2.0
        self.rate     = tk.DoubleVar(value=1.0)  # 0.5-4.0
        self.pitch    = tk.DoubleVar(value=1.0)  # 0.5-2.0
        self.emphasis = tk.DoubleVar(value=1.0)  # 0.0-2.0
        self.joy      = tk.DoubleVar(value=0.0)  # 0.0-1.0
        self.anger    = tk.DoubleVar(value=0.0)  # 0.0-1.0
        self.sadness  = tk.DoubleVar(value=0.0)  # 0.0-1.0

        self.friendly = tk.DoubleVar(value=1.0)
        self.trust = tk.DoubleVar(value=1.0)
        self.tension = tk.DoubleVar(value=1.0)

        self.person = tk.StringVar(value="nozomi_emo_22_standard")

        self.xyz_client = XYZClient()
        self.xyz_client.start()

        self.gaze_priority = tk.IntVar(value=4)
        self.gaze_keeptime = tk.DoubleVar(value=1)
        self.head_averted = tk.BooleanVar(value=True)
        self.head_amount  = tk.DoubleVar(value=0.3) # 0.0-1.0
        self.gaze_amount  = tk.DoubleVar(value=0.5)
        self.look_keeptime = tk.DoubleVar(value=2.5)

        self.speech_text  = tk.StringVar(value="こんにちは！いらっしゃいませ。今日はどのようなご用件でしょうか？何かお手伝いできることがあれば教えてくださいね。")
        self.speech_save = tk.BooleanVar(value=False)
        self.style_neutral = tk.IntVar(value=0)
        self.style_formality = tk.IntVar(value=0)
        self.style_intimacy = tk.IntVar(value=0)
        self.style_difficult = tk.IntVar(value=0) 
        self.style_easy = tk.IntVar(value=0) 
        self.style_complex = tk.IntVar(value=0)
        self.style_consideration = tk.IntVar(value=0)
        self.style_directness = tk.IntVar(value=0) 
        self.style_hedging = tk.IntVar(value=0)
        self.style_framing = tk.IntVar(value=0)
        self.style_choice = tk.IntVar(value=0)
        self.style_empathic = tk.IntVar(value=0)
        self.style_comprehensibility = tk.IntVar(value=0)
        self.style_paraphrase = tk.IntVar(value=0)
        self.style_repeat = tk.IntVar(value=0)
        self.style_duration = tk.IntVar(value=0)

        self.nod_amplitude = tk.IntVar(value=100) 
        self.nod_duration = tk.DoubleVar(value=0.4) 
        self.nod_times    = tk.IntVar(value=1)      # 1-3
        self.nod_priority = tk.IntVar(value=2)
        self.nod_lang = tk.BooleanVar(value=False)
        self.nod_emo = tk.BooleanVar(value=True)
        self.nod_facial_emotion_before = tk.StringVar(value="AffiliativeSmile")
        self.nod_emotion_level_before = tk.IntVar(value=2)
        self.nod_facial_emotion_after = tk.StringVar(value="WaitSmile")
        self.nod_emotion_level_after = tk.IntVar(value=2)
        self._player = AudioPlayer(autoremove=False)

        self.filler_vars = {
            filler: tk.BooleanVar(value=(filler in DEFAULT_SELECTED_FILLERS))
            for filler in FILLER_CANDIDATES
        }
        self.fillers_rate = tk.DoubleVar(value=0.7)

        self.filler_cant_hear_type = tk.StringVar(value="sorry")
        self.filler_cant_hear_level = tk.IntVar(value=1)
        self.filler_cant_hear_voice_type = tk.StringVar(value="すみません。もう一度よろしいでしょうか？")
        self.filler_cant_hear_voice_level = tk.IntVar(value=1) #0:notSpeaking, 1:Speaking

        self.filler_listen_type = tk.StringVar(value="AffiliativeSmileOpenEyes")
        self.filler_listen_level = tk.IntVar(value=3)
        self.filler_listen_nod_type = tk.StringVar(value="small")
        self.filler_listen_nod_time = tk.IntVar(value=1)
        self.filler_listen_voice_type = tk.StringVar(value="うん")
        self.filler_listen_voice_level = tk.IntVar(value=0)
        self.filler_listen_emotion_type = tk.StringVar(value="AffiliativeSmile")
        self.filler_listen_emotion_level = tk.IntVar(value=2)

        self.filler_understand_type = tk.StringVar(value="RewardSmile")
        self.filler_understand_level = tk.IntVar(value=2)
        self.filler_understand_nod_type = tk.StringVar(value="small")
        self.filler_understand_nod_level = tk.IntVar(value=7)
        self.filler_understand_voice_type = tk.StringVar(value="はい")
        self.filler_understand_voice_level = tk.IntVar(value=1) #0:notSpeaking, 1:Speaking

        self.filler_think_type = tk.StringVar(value="WaitSmile")
        self.filler_think_level = tk.IntVar(value=3)

        self.filler_think_gaze_type = tk.StringVar(value="d")
        self.filler_think_gaze_amount = tk.DoubleVar(value=0.5)

        self.filler_speak_gaze_type = tk.StringVar(value="d")
        self.filler_speak_gaze_amount = tk.DoubleVar(value=0.5)

        self.filler_speak_gaze_matchtime = tk.DoubleVar(value=2.0)
        self.filler_speak_gaze_averttime = tk.DoubleVar(value=2.0)

        self.filler_speak_face_type = tk.StringVar(value="AffiliativeSmile")
        self.filler_speak_face_level = tk.IntVar(value=2)

        self._loading_settings = False
        self.settings_file_name = tk.StringVar(value="default")
        self.selected_file_name = tk.StringVar(value="default.json")

        self._gaze_name_to_code = {name: code for name, code in GAZE_DIRS}
        self._gaze_code_to_name = {code: name for name, code in GAZE_DIRS}
        self._gaze_names = [name for name, _ in GAZE_DIRS]

        # ===== 感情別 voice_state_emo.json 用 =====
        self.emo_voice_keys = ("greeting", "thanks", "apology", "explanation")
        self.emo_voice_vars = {}

        voice_defaults = {
            "greeting":    {"volume": 1.3, "rate": 1.02, "pitch": 1.0,  "emphasis": 1.08, "joy": 0.8,  "anger": 0.0, "sadness": 0.0},
            "thanks":      {"volume": 1.3, "rate": 0.98, "pitch": 1.03, "emphasis": 1.05, "joy": 0.12, "anger": 0.0, "sadness": 0.0},
            "apology":     {"volume": 1.2, "rate": 0.92, "pitch": 0.96, "emphasis": 0.95, "joy": 0.0,  "anger": 0.0, "sadness": 0.18},
            "explanation": {"volume": 1.3, "rate": 1.0,  "pitch": 1.0,  "emphasis": 1.0,  "joy": 0.0,  "anger": 0.0, "sadness": 0.0},
        }

        for key in self.emo_voice_keys:
            d = voice_defaults[key]
            self.emo_voice_vars[key] = {
                "volume": tk.DoubleVar(value=d["volume"]),
                "rate": tk.DoubleVar(value=d["rate"]),
                "pitch": tk.DoubleVar(value=d["pitch"]),
                "emphasis": tk.DoubleVar(value=d["emphasis"]),
                "joy": tk.DoubleVar(value=d["joy"]),
                "anger": tk.DoubleVar(value=d["anger"]),
                "sadness": tk.DoubleVar(value=d["sadness"]),
            }

        # ===== 感情別 motion_state.json 用 =====
        self.emo_motion_keys = ("greeting", "thanks", "apology", "explanation")
        self.emo_motion_vars = {}

        motion_defaults = {
            "greeting": {
                "face_type": "AffiliativeSmile",
                "face_level": 2,
                "bow_enabled": False,
                "bow_kind": "none",
                "between_gaze_type": "l",
                "between_gaze_level": 0.4,
                "end_gaze_return": True,
            },
            "thanks": {
                "face_type": "RewardSmile",
                "face_level": 2,
                "bow_enabled": True,
                "bow_kind": "small",
                "between_gaze_type": "d",
                "between_gaze_level": 0.5,
                "end_gaze_return": True,
            },
            "apology": {
                "face_type": "WaitSmile",
                "face_level": 1,
                "bow_enabled": True,
                "bow_kind": "deep",
                "between_gaze_type": "ld",
                "between_gaze_level": 0.6,
                "end_gaze_return": True,
            },
            "explanation": {
                "face_type": "neutral",
                "face_level": 1,
                "bow_enabled": False,
                "bow_kind": "none",
                "between_gaze_type": "l",
                "between_gaze_level": 0.3,
                "end_gaze_return": True,
            },
        }

        for key in self.emo_motion_keys:
            d = motion_defaults[key]
            self.emo_motion_vars[key] = {
                "face_type": tk.StringVar(value=d["face_type"]),
                "face_level": tk.IntVar(value=d["face_level"]),
                "bow_enabled": tk.BooleanVar(value=d["bow_enabled"]),
                "bow_kind": tk.StringVar(value=d["bow_kind"]),
                "between_gaze_type": tk.StringVar(value=d["between_gaze_type"]),
                "between_gaze_level": tk.DoubleVar(value=d["between_gaze_level"]),
                "end_gaze_return": tk.BooleanVar(value=d["end_gaze_return"]),
            }

        # TCP関連
        self.sock: socket.socket | None = None
        self._terminator = self._eol_bytes(TCP_EOL)

        self._build_ui()

        if USE_TCP:
            self._connect_tcp()
            self._log(f"TCP接続モード: {TCP_HOST}:{TCP_PORT} terminator={self._terminator!r}")
        else:
            self._log("HTTP送信モード")

        # 終了時処理
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        for v in (self.volume, self.rate, self.pitch, self.emphasis, self.joy, self.anger, self.sadness):
            v.trace_add("write", lambda *args: self._write_voice_state())

        for var in list(self.filler_vars.values()) + [self.fillers_rate]:
            var.trace_add("write", lambda *args: self._write_filler_state())

        for v in (
            self.filler_cant_hear_type, self.filler_cant_hear_level, 
            self.filler_cant_hear_voice_type, self.filler_cant_hear_voice_level,
            self.filler_listen_type,    self.filler_listen_level, 
            self.filler_listen_nod_type, self.filler_listen_nod_time,
            self.filler_listen_voice_type, self.filler_listen_voice_level,
            self.filler_listen_emotion_type, self.filler_listen_emotion_level,
            self.filler_understand_type, self.filler_understand_level,
            self.filler_understand_nod_type, self.filler_understand_nod_level, 
            self.filler_understand_voice_type, self.filler_understand_voice_level,   
            self.filler_think_type,     self.filler_think_level,
            self.filler_think_gaze_type, self.filler_think_gaze_amount, 
            self.filler_speak_face_type, self.filler_speak_face_level,
            self.filler_speak_gaze_type, self.filler_speak_gaze_amount,
            self.filler_speak_gaze_matchtime, self.filler_speak_gaze_averttime,
            self.person, self.style_formality,
        ):
            v.trace_add("write", lambda *args: self._write_filler_face_state())

        for v in (
            self.style_neutral, 
            self.style_formality, self.style_intimacy,
            self.style_difficult, self.style_easy, self.style_complex,
            self.style_consideration, self.style_directness, self.style_hedging,
            self.style_framing, self.style_choice, self.style_empathic,
            self.style_comprehensibility, self.style_paraphrase,self.style_repeat,
            self.style_duration
        ):
            v.trace_add("write", lambda *args: self._write_speaking_style_state())

        for key in self.emo_voice_keys:
            for var in self.emo_voice_vars[key].values():
                var.trace_add("write", lambda *args: self._write_voice_state_emo())

        for key in self.emo_motion_keys:
            for var in self.emo_motion_vars[key].values():
                var.trace_add("write", lambda *args: self._write_motion_state())

        # 起動直後にも一度書き出す
        self._write_voice_state()
        self._write_filler_face_state()
        self._write_voice_state_emo()
        self._write_motion_state()


    def _current_tts_instructions(self) -> dict:
        return {
            "tts_volume": round(self.volume.get(), 2),
            "tts_rate": round(self.rate.get(), 2),
            "tts_pitch": round(self.pitch.get(), 2),
            "tts_emphasis": round(self.emphasis.get(), 2),
            "tts_emo_joy": round(self.joy.get(), 2),
            "tts_emo_angry": round(self.anger.get(), 2),
            "tts_emo_sad": round(self.sadness.get(), 2),
        }
    
    def _get_selected_fillers(self) -> set[str]:
        return {
            filler
            for filler, var in self.filler_vars.items()
            if var.get()
        }

    def _write_voice_state(self):
        """chatbot_tcp_tts.py が読む voice_state.json を更新する。"""
        try:
            payload = {
                "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "instructions": self._current_tts_instructions(),
            }
            VOICE_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            # UIは止めない
            self._log(f"! voice_state.json write error: {e}")

    def _write_filler_state(self):
        try:
            payload = {
                "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "fillers": sorted(self._get_selected_fillers()),
                "rate": round(self.fillers_rate.get(),2)
            }
            FILLER_VOICE_STATE_PATH.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            self._log(f"! filler_state.json write error: {e}")

    def _current_voice_state_emo(self) -> dict:
        voices = {}
        for key in self.emo_voice_keys:
            v = self.emo_voice_vars[key]
            voices[key] = {
                "tts_volume": round(v["volume"].get(), 2),
                "tts_rate": round(v["rate"].get(), 2),
                "tts_pitch": round(v["pitch"].get(), 2),
                "tts_emphasis": round(v["emphasis"].get(), 2),
                "tts_emo_joy": round(v["joy"].get(), 2),
                "tts_emo_angry": round(v["anger"].get(), 2),
                "tts_emo_sad": round(v["sadness"].get(), 2),
            }
        return {"voices": voices}

    def _write_voice_state_emo(self):
        try:
            payload = self._current_voice_state_emo()
            VOICE_STATE_EMO_PATH.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            self._log(f"! voice_state_emo.json write error: {e}")


    def _current_motion_state(self) -> dict:
        motions = {}
        for key in self.emo_motion_keys:
            m = self.emo_motion_vars[key]
            motions[key] = {
                "face": {
                    "type": m["face_type"].get(),
                    "level": int(m["face_level"].get()),
                },
                "bow": {
                    "enabled": bool(m["bow_enabled"].get()),
                    "kind": m["bow_kind"].get(),
                },
                "between_gaze": {
                    "type": m["between_gaze_type"].get(),
                    "level": round(m["between_gaze_level"].get(), 2),
                },
                "end_gaze_return": bool(m["end_gaze_return"].get()),
            }
        return {"motions": motions}

    def _write_motion_state(self):
        try:
            payload = self._current_motion_state()
            MOTION_STATE_PATH.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            self._log(f"! motion_state.json write error: {e}")

    def _current_speaking_style_state(self) -> dict:
        return {
            "neutral": int(self.style_neutral.get()),
            "formality": int(self.style_formality.get()),
            "intimacy": int(self.style_intimacy.get()),
            "difficult": int(self.style_difficult.get()),
            "easy": int(self.style_easy.get()),
            "complex": int(self.style_complex.get()),
            "consideration": int(self.style_consideration.get()),
            "directness": int(self.style_directness.get()),
            "hedging": int(self.style_hedging.get()),
            "framing": int(self.style_framing.get()),
            "choice": int(self.style_choice.get()),
            "empathic_phrasing": int(self.style_empathic.get()),
            "comprehensibility": int(self.style_comprehensibility.get()),
            "paraphrase_check":int(self.style_paraphrase.get()),
            "echo_repeat":int(self.style_repeat.get()),
            "duration": int(self.style_duration.get()),
        }

    def _write_speaking_style_state(self):
        try:
            payload = self._current_speaking_style_state()
            SPEAKING_STYLE_STATE_PATH.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            self._log(f"! write speaking style error: {e}")

    def _current_filler_face_state(self) -> dict:
        return {
            "cant_hear": {
                "type": self.filler_cant_hear_type.get(),
                "level": int(self.filler_cant_hear_level.get()),
            },
            "cant_hear_voice": {
                "type": self.filler_cant_hear_voice_type.get(),
                "level": int(self.filler_cant_hear_voice_level.get()),
            },
            "listen": {
                "type": self.filler_listen_type.get(),
                "level": int(self.filler_listen_level.get()),
            },
            "listen_nod": {
                "type": self.filler_listen_nod_type.get(),
                "level": int(self.filler_listen_nod_time.get()),
            },
            "listen_voice":{
                "type":self.filler_listen_voice_type.get(),
                "level": int(self.filler_listen_voice_level.get()),
            },
            "listen_emotion":{
                "type":self.filler_listen_emotion_type.get(),
                "level": int(self.filler_listen_emotion_level.get()),
            },
            "understand":{
                "type":self.filler_understand_type.get(),
                "level": int(self.filler_understand_level.get()),
            },
            "understand_nod":{
                "type":self.filler_understand_nod_type.get(),
                "level": int(self.filler_understand_nod_level.get()),
            },
            "understand_voice":{
                "type":self.filler_understand_voice_type.get(),
                "level": int(self.filler_understand_voice_level.get()),
            },
            "think": {
                "type": self.filler_think_type.get(),
                "level": int(self.filler_think_level.get()),
            },
            "think_gaze":{
                "type" : self.filler_think_gaze_type.get(),
                "level" : round(self.filler_think_gaze_amount.get(),2)
            },
            "speak_face": {
                "type": self.filler_speak_face_type.get(),
                "level": int(self.filler_speak_face_level.get()),
            },
            "speak_gaze": {
                "type": self.filler_speak_gaze_type.get(),
                "level": round(self.filler_speak_gaze_amount.get(),2),
            },
            "speak_gaze_match": {
                "type": "",
                "level": round(self.filler_speak_gaze_matchtime.get(),2),
            },
            "speak_gaze_avert": {
                "type": "",
                "level": round(self.filler_speak_gaze_averttime.get(),2),
            },
            "speak_person":{
                "type":self.person.get(),
                "level": int(self.style_formality.get()),
            },
        }

    def _write_filler_face_state(self):
        try:
            payload = {
                "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "faces": self._current_filler_face_state(),
            }
            FILLER_FACE_STATE_PATH.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            self._log(f"! filler_face_state.json write error: {e}")

    

    # ----------- UI ------------
    def _build_ui(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure("Selected.TButton", background="#66aaff")
        style.map("Selected.TButton",
                background=[("active", "#4488dd")])

        # ===== root を左右2カラムにする =====
        root.columnconfigure(0, weight=3)   # 左をやや広め
        root.columnconfigure(1, weight=2)
        root.rowconfigure(0, weight=1)

        left = ttk.Frame(root)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew")

        left.columnconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        # =========================
        # 左側
        # =========================

        # 1. 笑顔＋表情
        row1 = ttk.Frame(left)
        row1.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        row1.columnconfigure(0, weight=2)
        row1.columnconfigure(1, weight=1)

        smile_card = self._card(row1, "笑顔")
        smile_card.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._smile_buttons_pannel(smile_card)

        expr_card = self._card(row1, "表情")
        expr_card.grid(row=0, column=1, sticky="ew")
        self._expression_buttons_pannel(expr_card)

        # 2. 声質パラメータ＋声質パラメータ(上位)＋発話内容
        row2 = ttk.Frame(left)
        row2.grid(row=1, column=0, sticky="w", pady=(0, 10))

        CARD_W = 200

        row2.columnconfigure(0, minsize=CARD_W)
        row2.columnconfigure(1, minsize=CARD_W)
        row2.columnconfigure(2, minsize=CARD_W)

        voice_card = self._card(row2, "声質パラメータ")
        voice_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._voice_panel(voice_card)

        voice_abs_card = self._card(row2, "声質パラメータ(上位)")
        voice_abs_card.grid(row=0, column=1, sticky="nsew", padx=(0, 6))
        self._voice_panel_abstract(voice_abs_card)

        speak_card = self._card(row2, "発話内容")
        speak_card.grid(row=0, column=2, sticky="nsew")
        self._speech_panel(speak_card)

        # 3. うなずき＋視線
        row3 = ttk.Frame(left)
        row3.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        row3.columnconfigure(0, weight=1)
        row3.columnconfigure(1, weight=1)

        colum1 = ttk.Frame(row3)
        colum1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        nod_card = self._card(colum1, "うなずき")
        nod_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._nod_panel(nod_card)
        filler_card = self._card(colum1, "フィラー")
        filler_card.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        self._filler_panel(filler_card)

        gaze_card = self._card(row3, "視線・頭向き")
        gaze_card.grid(row=0, column=1, sticky="nsew")
        self._gaze_panel(gaze_card)

        # 4. ログ
        log_card = self._card(left, "ログ")
        log_card.grid(row=3, column=0, sticky="nsew", pady=(0, 0))
        left.rowconfigure(3, weight=1)

        self.log = ScrolledText(log_card, height=12)
        self.log.pack(fill="both", expand=True)

        # =========================
        # 右側
        # =========================

        voice_person_card = self._card(right, "話し手")
        voice_person_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._voice_panel_person(voice_person_card)

        emo_voice_card = self._card(right, "感情別 音声設定")
        emo_voice_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self._emo_voice_panel(emo_voice_card)

        emo_motion_card = self._card(right, "感情別 モーション設定")
        emo_motion_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self._emo_motion_panel(emo_motion_card)

        style_card = self._card(right, "話し方")
        style_card.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self._style_panel(style_card)

        filler_card = self._card(right, "Filler")
        filler_card.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self._filler_face_panel(filler_card)

        settings_card = self._card(right, "設定保存・読み込み")
        settings_card.grid(row=5, column=0, sticky="ew")
        self._settings_panel(settings_card)

    def _card(self, parent, title):
        frm = ttk.Labelframe(parent, text=title, padding=10)
        return frm
    
    def _smile_buttons_pannel(self, parent):
        # レベル選択（1-3）
        level_row = ttk.Frame(parent)
        level_row.pack(fill="x")
        ttk.Label(level_row, text="レベル").pack(side="left")
        for i in (1, 2, 3):
            ttk.Radiobutton(level_row, text=str(i), value=i, variable=self.smile_level).pack(side="left", padx=4)
        ttk.Spinbox(level_row, from_=1, to=10, textvariable=self.smile_priority, width=3).pack(side="right")
        ttk.Label(level_row, text="優先度").pack(side="right")
        # ボタン群
        grid = ttk.Frame(parent)
        grid.pack(fill="x", pady=(6, 0))

        self.smile_button = ttk.Button(
            grid, text="smile(目口)", width=12,
            command=lambda: self._on_button("expression","smile")
        )
        self.smile_button.grid(row=0, column=0, padx=6, pady=6, sticky="ew")

        self.laugh_button = ttk.Button(
            grid, text="laugh(口)", width=12,
            command=lambda: self._on_button("expression","laugh")
        )
        self.laugh_button.grid(row=0, column=1, padx=6, pady=6, sticky="ew")

        self.reset_button = ttk.Button(
            grid, text="リセット", width=12,
            command=lambda: self._on_button("expression","reset")
        )
        self.reset_button.grid(row=1, column=0, padx=6, pady=6, sticky="ew")

    def _expression_buttons_pannel(self, parent):
        # レベル選択（1-3）
        level_row = ttk.Frame(parent)
        level_row.pack(fill="x")
        self.expression_combo = ttk.Combobox(
            level_row, values=self.facial_emotions, width=10,
            textvariable=self.facial_emotion
        )
        self.expression_combo.pack(side="left")
        self.expression_combo.bind("<<ComboboxSelected>>", self._update_emotion_button_text)

        ttk.Label(level_row, text="レベル").pack(side="left")
        for i in (1, 2, 3):
            ttk.Radiobutton(level_row, text=str(i), value=i, variable=self.emotion_level).pack(side="left", padx=4)
        ttk.Spinbox(level_row, from_=1, to=10, textvariable=self.emotion_priority, width=3).pack(side="right")
        ttk.Label(level_row, text="優先度").pack(side="right")

        grid = ttk.Frame(parent)
        grid.pack(fill="x")
        self.emotion_button_0=self._emotion_button(grid, self.facial_emotion.get())
        self.emotion_button_0.grid(row=0, column=0, padx=6, pady=6, sticky="ew")
        self.emotion_buttons["facial"] = self.emotion_button_0
        for col, payload in enumerate(SMILES, start=1):
            b = self._emotion_button(grid, payload)
            b.grid(row=0, column=col, padx=6, pady=6, sticky="ew")
            self.emotion_buttons[payload] = b

        self.emotion_button_n=self._emotion_button(grid, "neutral")
        self.emotion_button_n.grid(row=1, column=0, padx=6, pady=6, sticky="ew")
        self.emotion_buttons["neutral"] = self.emotion_button_n

    def _update_emotion_button_text(self, event=None):
        self.emotion_button.config(text=self.facial_emotion.get())

    def _voice_panel(self, parent):
        self._slider_row(parent, "音量", self.volume, 0.0, 2.0)
        self._slider_row(parent,"速さ", self.rate, 0.5, 2.0)
        self._slider_row(parent,"高さ", self.pitch, 0.5, 2.0)
        self._slider_row(parent,"強調", self.emphasis, 0.0, 2.0)

        ttk.Separator(parent).pack(fill="x", pady=6)

        self._slider_row(parent,"喜び", self.joy, 0.0, 1.0)
        self._slider_row(parent,"怒り", self.anger, 0.0, 1.0)
        self._slider_row(parent,"悲しみ", self.sadness, 0.0, 1.0)

    def _voice_panel_abstract(self, parent):
        self._slider_row(parent, "親しみ", self.friendly, 0.0, 2.0)
        self._slider_row(parent, "信頼性", self.trust, 0.0, 2.0)
        self._slider_row(parent, "テンション", self.tension, 0.0, 2.0)

        self.friendly.trace_add("write", lambda *args: None if getattr(self, "_loading_settings", False) else self.compute_abstract_voice())
        self.trust.trace_add("write", lambda *args: None if getattr(self, "_loading_settings", False) else self.compute_abstract_voice())
        self.tension.trace_add("write", lambda *args: None if getattr(self, "_loading_settings", False) else self.compute_abstract_voice())
        
        reset_btn = ttk.Button(parent, text="抽象＋声質パラメータをリセット",
                           command=self.reset_voice_params)
        reset_btn.pack(pady=10)

    def _voice_panel_person(self, parent):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)

        combo = ttk.Combobox(row, values=PERSON, width=22, textvariable=self.person)
        combo.pack(side="left", padx=6)

        ttk.Button(row, text="変更する", command=self._change_person).pack(side="left")

    def _emo_voice_panel(self, parent):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)
        for i, key in enumerate(self.emo_voice_keys):
            box = ttk.Labelframe(row, text=key, padding=8)
            box.grid(row=0, column=i, sticky="nsew")

            v = self.emo_voice_vars[key]
            self._slider_row(box, "音量", v["volume"], 0.0, 2.0)
            self._slider_row(box, "速さ", v["rate"], 0.5, 2.0)
            self._slider_row(box, "高さ", v["pitch"], 0.5, 2.0)
            self._slider_row(box, "強調", v["emphasis"], 0.0, 2.0)
            ttk.Separator(box).pack(fill="x", pady=6)
            self._slider_row(box, "喜び", v["joy"], 0.0, 1.0)
            self._slider_row(box, "怒り", v["anger"], 0.0, 1.0)
            self._slider_row(box, "悲しみ", v["sadness"], 0.0, 1.0)

    def _emo_motion_panel(self, parent):
        bow_kinds = ["none", "small", "deep"]
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)
        for i,key in enumerate(self.emo_motion_keys):
            box = ttk.Labelframe(row, text=key, padding=8)
            box.grid(row=0, column=i, sticky="nsew")

            m = self.emo_motion_vars[key]

            row1 = ttk.Frame(box)
            row1.pack(fill="x", pady=2)

            ttk.Label(row1, text="表情", width=8).pack(side="left")
            ttk.Combobox(
                row1,
                values=FILLER_EMOTIONS,
                textvariable=m["face_type"],
                width=22
            ).pack(side="left", padx=4)

            row11 = ttk.Frame(box)
            row11.pack(fill="x", pady=2)

            ttk.Label(row11, text="Lv").pack(side="left", padx=(8, 0))
            for i in (1, 2, 3):
                ttk.Radiobutton(row11, text=str(i), value=i, variable=m["face_level"]).pack(side="left", padx=2)

            row2 = ttk.Frame(box)
            row2.pack(fill="x", pady=2)

            ttk.Label(row2, text="お辞儀", width=8).pack(side="left")
            ttk.Checkbutton(row2, text="有効", variable=m["bow_enabled"]).pack(side="left", padx=4)
            ttk.Label(row2, text="種類").pack(side="left", padx=(8, 0))
            ttk.Combobox(
                row2,
                values=bow_kinds,
                textvariable=m["bow_kind"],
                width=10,
                state="readonly"
            ).pack(side="left", padx=4)

            row3 = ttk.Frame(box)
            row3.pack(fill="x", pady=2)

            ttk.Label(row3, text="文間視線", width=8).pack(side="left")

            gaze_combo = ttk.Combobox(row3, values=self._gaze_names, width=10, state="readonly")
            gaze_combo.pack(side="left", padx=4)
            gaze_combo.set(self._gaze_code_to_name.get(m["between_gaze_type"].get(), "left"))

            def _make_gaze_handler(var, combo):
                def _on_selected(_evt=None):
                    name = combo.get()
                    var.set(self._gaze_name_to_code.get(name, "l"))
                return _on_selected

            gaze_combo.bind("<<ComboboxSelected>>", _make_gaze_handler(m["between_gaze_type"], gaze_combo))
            
            row31 = ttk.Frame(box)
            row31.pack(fill="x", pady=2)
            self._mini_slider(row31, "度合", m["between_gaze_level"], vmin=0.0, vmax=1.0)

            row4 = ttk.Frame(box)
            row4.pack(fill="x", pady=2)
            ttk.Label(row4, text="終了時").pack(side="left")
            ttk.Checkbutton(row4, text="視線戻し", variable=m["end_gaze_return"]).pack(side="left", padx=4)

    def _gaze_panel(self, parent):
        level_row = ttk.Frame(parent)
        level_row.pack(fill="x")
        self._slider_row(level_row, "時間", self.gaze_keeptime, 0.0, 5.0)
        ttk.Spinbox(level_row, from_=1, to=10, textvariable=self.gaze_priority, width=3).pack(side="right")
        ttk.Label(level_row, text="優先度").pack(side="right")
        
        row = ttk.Frame(parent); 
        row.pack(fill="x")
        ttk.Checkbutton(row, text="頭も", variable=self.head_averted).pack(side="left")
        ttk.Label(row, text="  度合").pack(side="left")
        self._slider_row(row, "", self.head_amount, 0.0, 1.0)
        row1 = ttk.Frame(parent); 
        row1.pack(fill="x")
        ttk.Label(row1, text=" 視線度合").pack(side="left")
        self._slider_row(row1, "", self.gaze_amount, 0.0, 1.0)

        pad = ttk.Frame(parent); pad.pack(pady=8)
        # 方向パッド 3x3
        
        for i,(name,command_name) in enumerate(GAZE_DIRS):
            r, c = divmod(i,3)
            b = ttk.Button(pad, text=name, width=10,
                           command=lambda cn=command_name: self._create_command("gaze", cn))
            b.grid(row=r, column=c, padx=4, pady=4)

        self._slider_row(parent, "時間", self.look_keeptime, 0.0, 5.0)
        reset_button=ttk.Button(parent, text="視線戻す", command=lambda: self._create_command("look", "reset"))
        reset_button.pack(side=tk.BOTTOM)

    def _speech_panel(self, parent):
        text = tk.Text(parent, height=7, width=30)
        text.pack(pady=4)

        # 初期値
        text.insert("1.0", self.speech_text.get())

        # Text → StringVar
        def on_text_change(event=None):
            self.speech_text.set(text.get("1.0", "end-1c"))

        text.bind("<KeyRelease>", on_text_change)

        # StringVar → Text
        def on_var_change(*args):
            current = text.get("1.0", "end-1c")
            new = self.speech_text.get()
            if current != new:
                text.delete("1.0", "end")
                text.insert("1.0", new)

        self.speech_text.trace_add("write", on_var_change)

        row = ttk.Frame(parent)
        row.pack(fill="x")

        ttk.Button(row, text="発話する", command=self._speak).pack(side="left")   
    
        ttk.Checkbutton(
            row,
            text="save",
            variable=self.speech_save
        ).pack(side="left", padx=8)
    
    def _style_panel(self, parent):
        self._tri_row(parent, "スタイル設定", self.style_neutral)

        self._tri_row_4(parent, [
            ("敬語", self.style_formality),
            ("親しさ", self.style_intimacy),
            ("専門性", self.style_difficult),
            ("語彙の易しさ", self.style_easy),
        ])
        self._tri_row_4(parent, [
            ("複雑さ", self.style_complex),
            ("配慮", self.style_consideration),
            ("直接性", self.style_directness),
            ("根拠提示", self.style_hedging),
        ])
        self._tri_row_4(parent, [
            ("代替提示", self.style_framing),
            ("選択肢の提示", self.style_choice),
            ("共感", self.style_empathic),
            ("わかりやすさ", self.style_comprehensibility),
        ])
        self._tri_row_4(parent, [
            ("言い換え", self.style_paraphrase),
            ("反復確認", self.style_repeat),
            ("長さ", self.style_duration),
        ])


    def _tri_row(self, parent, label, var):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)

        ttk.Label(row, text=label, width=10).pack(side="left")

        ttk.Radiobutton(row, text="有", value=0,  variable=var).pack(side="left", padx=2)
        ttk.Radiobutton(row, text="無", value=1,  variable=var).pack(side="left", padx=2)

    def _tri_row_4(self, parent, items):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)

        for col, (label, var) in enumerate(items):
            cell = ttk.Frame(row)
            cell.grid(row=0, column=col, padx=10, sticky="w")

            ttk.Label(cell, text=label, width=10).grid(row=0, column=0, sticky="w")

            ttk.Radiobutton(cell, text="-1", value=-1, variable=var).grid(row=0, column=1)
            ttk.Radiobutton(cell, text=" 0", value=0,  variable=var).grid(row=0, column=2)
            ttk.Radiobutton(cell, text="+1", value=1,  variable=var).grid(row=0, column=3)
    
    def _nod_panel(self, parent):
    # 時間スライダー
        self._slider_row(parent, "時間", self.nod_duration, 0.2, 1.2)
        ttk.Spinbox(parent, from_=1, to=10, textvariable=self.nod_priority, width=3).pack(side="right")
        ttk.Label(parent, text="回数").pack(side="right")

        others_row = ttk.Frame(parent)
        others_row.pack(fill="x", pady=6)

        # --- 発言 ---
        lang_frame = ttk.Frame(others_row)
        lang_frame.pack(side="left")

        ttk.Label(lang_frame, text="発言").pack(side="left")
        ttk.Radiobutton(lang_frame, text="有",
                        value=True, variable=self.nod_lang).pack(side="left", padx=4)
        ttk.Radiobutton(lang_frame, text="無",
                        value=False, variable=self.nod_lang).pack(side="left", padx=4)

        ttk.Frame(others_row, width=20).pack(side="left")

        # --- 表情 ---
        emo_frame = ttk.Frame(others_row)
        emo_frame.pack(side="left")

        # 左カラム（表情 有/無）
        emo_left = ttk.Frame(emo_frame)
        emo_left.pack(side="left", padx=(0, 12), anchor="n")  # 右側との間隔

        ttk.Label(emo_left, text="表情").pack(side="left")
        ttk.Radiobutton(emo_left, text="有", value=True,  variable=self.nod_emo).pack(side="left", padx=4)
        ttk.Radiobutton(emo_left, text="無", value=False, variable=self.nod_emo).pack(side="left", padx=4)

        # 右カラム（before/after を縦に）
        emo_right = ttk.Frame(emo_frame)
        emo_right.pack(side="left", anchor="n")

        # 1段目：Before
        before_row = ttk.Frame(emo_right)
        before_row.pack(fill="x", anchor="w", pady=(0, 4))

        ttk.Label(before_row, text="前").pack(side="left", padx=(0, 4))
        self.expression_combo_before = ttk.Combobox(
            before_row, values=self.facial_emotions, width=10,
            textvariable=self.nod_facial_emotion_before
        )
        self.expression_combo_before.pack(side="left")

        ttk.Label(before_row, text="レベル").pack(side="left", padx=(8, 0))
        for i in (1, 2, 3):
            ttk.Radiobutton(before_row, text=str(i), value=i,
                            variable=self.nod_emotion_level_before).pack(side="left", padx=2)

        # 2段目：After
        after_row = ttk.Frame(emo_right)
        after_row.pack(fill="x", anchor="w")

        ttk.Label(after_row, text="後").pack(side="left", padx=(0, 4))
        self.expression_combo_after = ttk.Combobox(
            after_row, values=self.facial_emotions, width=10,
            textvariable=self.nod_facial_emotion_after
        )
        self.expression_combo_after.pack(side="left")

        ttk.Label(after_row, text="レベル").pack(side="left", padx=(8, 0))
        for i in (1, 2, 3):
            ttk.Radiobutton(after_row, text=str(i), value=i,
                            variable=self.nod_emotion_level_after).pack(side="left", padx=2)

        # 見出し
        grid = ttk.Frame(parent)
        grid.pack(fill="x", pady=6)
        ttk.Label(grid, text="").grid(row=0, column=0)
        for j, label in enumerate(("小", "中", "大"), start=1):
            ttk.Label(grid, text=label).grid(row=0, column=j, padx=6)

        # パラメータ定義
        others = [True,False]
        

        for i, other in enumerate(others, start=1):
            if(other==False):
                ttk.Label(grid, text="無").grid(row=i, column=0, padx=(0,8))
            else:
                ttk.Label(grid, text="有").grid(row=i, column=0, padx=(0,8))

            for j, (scale, amp) in enumerate(NOD_AMPLITUDES.items(), start=1):
                if scale=="small":
                    ttk.Button(
                        grid,
                        text=f"{scale}",
                        width=6,
                        command=lambda s=scale, o=other, a=amp: self._create_backchannel(
                            s, {
                                "duration": round(self.nod_duration.get(), 2),
                                "other" : o,
                                "amplitude": a,
                            })
                    ).grid(row=i, column=j, padx=4, pady=2)
                elif scale=="mid":
                    ttk.Button(
                        grid,
                        text=f"{scale}",
                        width=6,
                        command=lambda s=scale, o=other, a=amp: self._create_backchannel(
                            s, {
                                "duration": round(self.nod_duration.get()*1.5, 2),
                                "other" : o,
                                "amplitude": a,
                            })
                    ).grid(row=i, column=j, padx=4, pady=2)
                elif scale == "large":
                    ttk.Button(
                        grid,
                        text=f"{scale}",
                        width=6,
                        command=lambda s=scale, o=other, a=amp: self._create_backchannel(
                            s, {
                                "duration": round(self.nod_duration.get()*2.0, 2),
                                "other" : o,
                                "amplitude": a,
                            })
                    ).grid(row=i, column=j, padx=4, pady=2)

    def _filler_panel(self,parent):
        filler_frame = ttk.LabelFrame(parent, text="待ち時間フィラー")
        filler_frame.pack(fill="x", pady=8)

        for i, filler in enumerate(FILLER_CANDIDATES):
            col = i // 3
            row = i % 3
            cb = ttk.Checkbutton(
                filler_frame,
                text=filler,
                variable=self.filler_vars[filler]
            )
            cb.grid(row=row, column=col, sticky="w", padx=8, pady=4)

        self._slider_row(parent, "割合", self.fillers_rate, 0.0, 1.0)

        

    def _filler_face_panel(self, parent):
        def one_row(title, type_var, level_var, test_key: str):
            row = ttk.Frame(parent)
            row.pack(fill="x", pady=4)

            ttk.Label(row, text=title, width=10).pack(side="left")

            combo = ttk.Combobox(row, values=FILLER_EMOTIONS, width=22, textvariable=type_var)
            combo.pack(side="left", padx=6)

            ttk.Label(row, text="Lv").pack(side="left")
            for i in (1,2,3):
                ttk.Radiobutton(row, text=str(i), value=i, variable=level_var).pack(side="left", padx=2)

            ttk.Separator(row, orient="vertical").pack(side="left", fill="y", padx=8)
            
            if test_key == "cant_hear":
                ttk.Label(row, text="音声").pack(side="left")
                nod_combo = ttk.Combobox(row, values=CANT_HEAR_VOICE, width=20,textvariable=self.filler_cant_hear_voice_type)
                nod_combo.pack(side="left", padx=6)
                ttk.Radiobutton(row, text="有",
                                value=1, variable=self.filler_cant_hear_voice_level).pack(side="left", padx=4)
                ttk.Radiobutton(row, text="無",
                                value=0, variable=self.filler_cant_hear_voice_level).pack(side="left", padx=4)
            
            if test_key == "listen":
                ttk.Label(row, text="頷き").pack(side="left")
                nod_combo = ttk.Combobox(row, values=["small","mid","large"], width=10,textvariable=self.filler_listen_nod_type)
                nod_combo.pack(side="left", padx=6)

                def _on_nod_selected(_evt=None):
                    name = nod_combo.get()
                    dir_path = Path(f"back_channels_{name}")
                    wav_files = list(dir_path.glob("*.wav"))
                    self.filler_listen_voice_type.set(str(random.choice(wav_files)))
                        
                nod_combo.bind("<<ComboboxSelected>>", _on_nod_selected)

                ttk.Label(row, text="回数").pack(side="left")
                ttk.Spinbox(row, from_=1, to=10, textvariable=self.filler_listen_nod_time, width=3).pack(side="left")
            
                ttk.Separator(row, orient="vertical").pack(side="left", fill="y", padx=8)
                
                ttk.Label(row, text="音声").pack(side="left")
                ttk.Radiobutton(row, text="有",
                                value=1, variable=self.filler_listen_voice_level).pack(side="left", padx=4)
                ttk.Radiobutton(row, text="無",
                                value=0, variable=self.filler_listen_voice_level).pack(side="left", padx=4)

                ttk.Separator(row, orient="vertical").pack(side="left", fill="y", padx=8)
                
                ttk.Label(row, text="表情").pack(side="left", padx=(0, 4))
                self.expression_combo_before = ttk.Combobox(
                    row, values=self.facial_emotions, width=10,
                    textvariable=self.filler_listen_emotion_type
                )
                self.expression_combo_before.pack(side="left")

                ttk.Label(row, text="レベル").pack(side="left", padx=(8, 0))
                for i in (1, 2, 3):
                    ttk.Radiobutton(row, text=str(i), value=i,
                                    variable=self.filler_listen_emotion_level).pack(side="left", padx=2)

            if test_key == "understand":
                ttk.Label(row, text="頷き").pack(side="left")
                nod_combo = ttk.Combobox(row, values=["small","mid","large"], width=10,textvariable=self.filler_understand_nod_type)
                nod_combo.pack(side="left", padx=6)

                def _on_nod_selected(_evt=None):
                    name = nod_combo.get()
                    dir_path = Path(f"back_channels_{name}")
                    wav_files = list(dir_path.glob("*.wav"))
                    self.filler_understand_voice_type.set(str(random.choice(wav_files)))
                    self.filler_understand_nod_level.set(int(NOD_AMPLITUDES[name]))
                        
                nod_combo.bind("<<ComboboxSelected>>", _on_nod_selected)

                ttk.Separator(row, orient="vertical").pack(side="left", fill="y", padx=8)
                
                ttk.Label(row, text="音声").pack(side="left")
                ttk.Radiobutton(row, text="有",
                                value=1, variable=self.filler_understand_voice_level).pack(side="left", padx=4)
                ttk.Radiobutton(row, text="無",
                                value=0, variable=self.filler_understand_voice_level).pack(side="left", padx=4)

            if test_key == "think":
                ttk.Label(row, text="視線").pack(side="left")

                gaze_combo = ttk.Combobox(row, values=self._gaze_names, width=10, state="readonly")
                gaze_combo.pack(side="left", padx=4)
                gaze_combo.set(self._gaze_code_to_name.get(self.filler_think_gaze_type.get(), "down"))

                def _on_gaze_selected(_evt=None):
                    name = gaze_combo.get()
                    self.filler_think_gaze_type.set(self._gaze_name_to_code.get(name, "d"))

                gaze_combo.bind("<<ComboboxSelected>>", _on_gaze_selected)

                self._mini_slider(row, "度合", self.filler_think_gaze_amount)

            if test_key == "speak":
                ttk.Label(row, text="視線").pack(side="left")

                gaze_combo = ttk.Combobox(row, values=self._gaze_names, width=10, state="readonly")
                gaze_combo.pack(side="left", padx=4)
                gaze_combo.set(self._gaze_code_to_name.get(self.filler_speak_gaze_type.get(), "down"))

                def _on_gaze_selected(_evt=None):
                    name = gaze_combo.get()
                    self.filler_speak_gaze_type.set(self._gaze_name_to_code.get(name, "d"))

                gaze_combo.bind("<<ComboboxSelected>>", _on_gaze_selected)

                self._mini_slider(row, "度合", self.filler_speak_gaze_amount)

                ttk.Separator(row, orient="vertical").pack(side="left", fill="y", padx=8)
                self._mini_slider(row, "合わせる", self.filler_speak_gaze_matchtime, vmax=4.0)
                ttk.Separator(row, orient="vertical").pack(side="left", fill="y", padx=8)
                self._mini_slider(row, "そらす", self.filler_speak_gaze_averttime, vmax=4.0)

        one_row("聞こえない", self.filler_cant_hear_type, self.filler_cant_hear_level, "cant_hear")
        one_row("聞いてる",   self.filler_listen_type, self.filler_listen_level, "listen")
        one_row("理解した",   self.filler_understand_type, self.filler_understand_level, "understand")
        one_row("考えてる",   self.filler_think_type, self.filler_think_level, "think")
        one_row("話している", self.filler_speak_face_type, self.filler_speak_face_level, "speak")

    def _test_filler_face(self, key: str):
        faces = self._current_filler_face_state()
        f = faces.get(key)
        if not f:
            return
        cmd = f"/emotion {f['type']} {f['level']} 1 1000"
        self._send_command(cmd)

    def _settings_panel(self, parent):
        row = ttk.Frame(parent)
        row.pack(fill="x")

        ttk.Label(row, text="保存名").pack(side="left", padx=3)
        tk.Entry(row, textvariable=self.settings_file_name).pack(side="left")
        ttk.Label(row, text=".json").pack(side="left", padx=3)
        ttk.Button(row, text="設定保存", command=self.save_settings).pack(side="left", padx=6)

        ttk.Label(row, text="読み込みファイルを選択").pack(side="left", padx=3)
        self.file_combo = ttk.Combobox(
            row,
            textvariable=self.selected_file_name,
            values=sorted(
                [file.name for file in Path("settings").iterdir() if file.is_file()]
            ),
            state="readonly",
            width=40
        )
        self.file_combo.pack(side="left", padx=3)
        ttk.Button(row, text="設定読込", command=self.load_settings).pack(side="left", padx=6)

        ttk.Button(row, text="ファイル再読み込み", command=self.reload_settings_file).pack(side="left", padx=6)

    ## 保存した変数の保存、読み込み
    def save_settings(self):
        data = {}

        for name, var in self.__dict__.items():
            if isinstance(var, (tk.IntVar, tk.DoubleVar, tk.StringVar, tk.BooleanVar)):
                data[name] = var.get()

        data["emo_voice_state"] = {
            key: {k: v.get() for k, v in self.emo_voice_vars[key].items()}
            for key in self.emo_voice_keys
        }

        data["emo_motion_state"] = {
            key: {k: v.get() for k, v in self.emo_motion_vars[key].items()}
            for key in self.emo_motion_keys
        }

        file_path = Path("settings") / f"{self.settings_file_name.get()}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._log(text=f"{self.settings_file_name.get()}.jsonを保存しました")

    def load_settings(self):
        self._loading_settings = True
        try:
            file_path = Path("settings") / self.selected_file_name.get()
            self._log(text=f"{self.selected_file_name.get()}を読み込みました")
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for name, value in data.items():
                if name in ("emo_voice_state", "emo_motion_state"):
                    continue
                var = getattr(self, name, None)
                if isinstance(var, (tk.IntVar, tk.DoubleVar, tk.StringVar, tk.BooleanVar)):
                    var.set(value)

            emo_voice_state = data.get("emo_voice_state", {})
            for key, values in emo_voice_state.items():
                if key in self.emo_voice_vars:
                    for name, value in values.items():
                        self.emo_voice_vars[key][name].set(value)

            emo_motion_state = data.get("emo_motion_state", {})
            for key, values in emo_motion_state.items():
                if key in self.emo_motion_vars:
                    for name, value in values.items():
                        self.emo_motion_vars[key][name].set(value)

            self.update_idletasks()

        finally:
            self._loading_settings = False

    def reload_settings_file(self):
        files = sorted([file.name for file in Path("settings").iterdir() if file.is_file()])
        self.file_combo["values"] = files
        if files:
            self.file_combo.current(0)
            self._log(text=f"ファイルを更新しました")


    # ----------- コンポーネント -----------
    def _emotion_button(self, grid, text):
        button = ttk.Button(
            grid,
            text=text,
            width=12,
            command=lambda: self._on_button("emotion", text)
        )
        return button

    def _slider_row(self, parent, label, var, vmin, vmax):
        row = ttk.Frame(parent); row.pack(fill="x", pady=3)

        ttk.Label(row, text=label, width=6).pack(side="left")

        # 表示ラベル
        val = ttk.Label(row, text=f"{var.get():.2f}")
        val.pack(side="left", padx=6)

        ttk.Label(row, text=f"{vmin:.2f}").pack(side="left")

        # スライダー本体
        s = ttk.Scale(row, variable=var, from_=vmin, to=vmax, orient="horizontal")
        s.pack(side="left", fill="x", expand=True, padx=8)

        ttk.Label(row, text=f"{vmax:.2f}").pack(side="left")

        # 手動で動かしたときの更新
        def on_move(_):
            val.config(text=f"{var.get():.2f}")

        s.bind("<B1-Motion>", on_move)
        s.bind("<ButtonRelease-1>", on_move)

        # ★ プログラム側で値が変わっても表示更新されるようにする
        var.trace_add("write", lambda *args: val.config(text=f"{var.get():.2f}"))

    def _mini_slider(self, parent, label_text, var, vmin=0.0, vmax=1.0, length=110):
        frame = ttk.Frame(parent)
        frame.pack(side="left", fill="x", padx=4)

        ttk.Label(frame, text=label_text).pack(side="left", padx=(2, 0))

        scale = ttk.Scale(
            frame,
            from_=vmin,
            to=vmax,
            variable=var,
            orient="horizontal",
            length=length
        )
        scale.pack(side="left", padx=4)

        val_label = ttk.Label(frame, width=4, anchor="e")
        val_label.pack(side="left")

        def _update_label(*_):
            val_label.config(text=f"{var.get():.2f}")

        var.trace_add("write", _update_label)
        _update_label()

        return frame

    # ----------- アクション -----------
    def _on_button(self, type, payload):
        self._update_ui_state(payload)
        self._create_command(type, payload)

    def _update_ui_state(self, payload):
        # カテゴリA: smile / laugh（ここはこの中だけ排他）
        face_actions = {
            "smile": self.smile_button,
            "laugh": self.laugh_button,
        }

        # カテゴリB: 感情・表情セット（ここはこの中だけ排他）
        emotions = dict(self.emotion_buttons)
        emotions["facial"] = self.emotion_button_0

        # reset: どのカテゴリを外すかを決めて処理（今の挙動を踏襲）
        if payload == "reset":
            if self.smile_flag.get():
                face_actions["smile"].configure(style="TButton")
            if self.laugh_flag.get():
                face_actions["laugh"].configure(style="TButton")
            return

        # payload -> (カテゴリ, キー) を決める
        if payload in face_actions:
            group = face_actions
            key = payload
        elif payload in self.facial_emotions:
            group = emotions
            key = "facial"
        elif payload in emotions:
            group = emotions
            key = payload
        else:
            return

        # 選ばれたカテゴリだけリセットして、その1つだけ Selected
        for b in group.values():
            b.configure(style="TButton")
        group[key].configure(style="Selected.TButton")


    
    def lerp(self, base, target, control_value, base_point=1.0, target_point=1.5):
        ratio = (control_value - base_point) / (target_point - base_point)
        return base + (target - base) * ratio

    def clamp(self, v, vmin, vmax):
        return max(vmin, min(v, vmax))

    def add_modifier(self, params, control_value, mapping):

        for key, (base, target) in mapping.items():
            delta = target - base
            ratio = (control_value - 1.0) / (1.5 - 1.0)
            params[key] += delta * ratio

        return params

    def compute_abstract_voice(self):
        """親しみ・信頼性・テンション → volume/pitch 等に反映"""

        params = {
            "volume": 1.3,
            "rate": 1.0,
            "pitch": 1.0,
            "emphasis": 1.0,
            "joy": 0.0,
            "anger": 0.0,
            "sadness": 0.0,
        }
        # 親しみ → 信頼性 → テンション の順に適用
        params = self.add_modifier(params, self.friendly.get(), FRIENDLY_MAP)
        params = self.add_modifier(params, self.trust.get(), TRUST_MAP)
        params = self.add_modifier(params, self.tension.get(), TENSION_MAP)

        for key, (vmin, vmax) in VOICE_RANGE.items():
            params[key] = self.clamp(params[key], vmin, vmax)

        # UI スライダーを更新する
        self.volume.set(params["volume"])
        self.rate.set(params["rate"])
        self.pitch.set(params["pitch"])
        self.emphasis.set(params["emphasis"])
        self.joy.set(params["joy"])
        self.anger.set(params["anger"])
        self.sadness.set(params["sadness"])

    ## パラメータをデフォルトに戻す
    def reset_voice_params(self):
        self.friendly.set(1.0)
        self.trust.set(1.0)
        self.tension.set(1.0)
        self.volume.set(1.3)
        self.rate.set(1.0)
        self.pitch.set(1.0)
        self.emphasis.set(1.0)
        self.joy.set(0.0)
        self.anger.set(0.0)
        self.sadness.set(0.0)
        self.compute_abstract_voice()
        self._log("声質パラメータと抽象パラメータをリセットしました。")

    def _create_backchannel(self, scale, payload):
        if payload["other"] & self.nod_lang.get():
            dir_path = Path(f"back_channels_{scale}")
            wav_files = list(dir_path.glob("*.wav"))
            wav_path = random.choice(wav_files)
            self._player.play_later(wav_path)

        self._create_command("nod",payload)
        time.sleep(0.1)
        duration = payload["duration"]*1000*0.9
        self._send_command(f"/blink {duration}")

        if payload["other"] & self.nod_emo.get():
            time.sleep(0.1)
            type = self.nod_facial_emotion_before.get()
            level = self.nod_emotion_level_before.get()
            priority = self.emotion_priority.get()
            keeptime = duration = payload["duration"]*1000*1.3
            command = f"/emotion {type} {level} {priority} {keeptime}"
            self._send_command(command)
            time.sleep(payload["duration"]*3)
            type = self.nod_facial_emotion_after.get()
            level = self.nod_emotion_level_after.get()
            command = f"/emotion {type} {level} {priority} {keeptime}"
            self._send_command(command)


    def _create_command(self, cmd_type, payload):
        if(cmd_type=="expression"):
            smile_level =  self.smile_level.get()
            smile_priority = self.smile_priority.get()
            keeptime = self.default_keeptime.get()
            if(payload=="smile"):
                command = f"/smile start {smile_level} {smile_priority} {keeptime}"
                self.smile_flag.set(True)
            elif(payload=="laugh"):
                command = f"/laugh start {smile_level} {smile_priority} {keeptime}"
                self.laugh_flag.set(True)
            else:
                if self.smile_flag.get():
                    command = f"/smile end"
                    self.smile_flag.set(False)
                elif self.laugh_flag.get():
                    command = f"/laugh end"
                    self.laugh_flag.set(False)
                else:
                    command = f"/smile end"
                    self.smile_flag.set(False)
        elif(cmd_type=="emotion"):
            type = payload
            level = self.emotion_level.get()
            priority = self.emotion_priority.get()
            keeptime = self.default_keeptime.get()
            command = f"/emotion {type} {level} {priority} {keeptime}"
            if payload=="neutral":
                self.emotion_flag.set(False)
            else:
                self.emotion_flag.set(True)
        elif(cmd_type=="gaze"):
            priority = self.gaze_priority.get()
            keeptime = round(self.gaze_keeptime.get(),2)*1000
            delta = 400 * round(self.gaze_amount.get(),2)
            sample = self.xyz_client.get_latest()
            x = sample.x
            y = sample.y
            z = sample.z
            if "u" in payload:
                z += 800 * round(self.gaze_amount.get(),2)
            if "d" in payload:
                z -= 200 * round(self.gaze_amount.get(),2)
            if "l" in payload:
                y -= delta
            if "r" in payload:
                y += delta
            if self.head_averted.get():
                level = round(self.head_amount.get(),2)
                command = f"/look {x} {y} {z} {round(1-level,2)} {level} 0 {priority} {keeptime}"
            else:
                command = f"/lookaway {payload} {priority} {keeptime}"
        elif(cmd_type=="look"):
            sample = self.xyz_client.get_latest()
            priority = self.gaze_priority.get() + 1
            keeptime = round(self.look_keeptime.get(),2)*1000
            command = f"/look {sample.x} {sample.y} {sample.z} 0.7 0.3 0 {priority} {keeptime}"
        elif(cmd_type=="nod"):
            priority = self.nod_priority.get()
            duration = payload["duration"]*1000 
            command = f"/nod {payload["amplitude"]} {duration} {priority} 2"

        else:
            command = f"/{cmd_type} {json.dumps(payload, ensure_ascii=False)}"
        
        self._send_command(command)

    def _speak(self):
        text = self.speech_text.get().strip()
        url = TTS_URL

        instructions = {
            "tts_volume": round(self.volume.get(),2),      
            "tts_rate": round(self.rate.get(),2),          
            "tts_pitch": round(self.pitch.get(),2),         
            "tts_emphasis": round(self.emphasis.get(),2),    
            "tts_emo_joy": round(self.joy.get(),2),      
            "tts_emo_angry": round(self.anger.get(),2),     
            "tts_emo_sad": round(self.sadness.get(),2)     
        }
        person = self.person.get()
        autoremove = not self.speech_save.get()
        tts.speak_async(text, instructions, url, autoremove, person)

    def _change_person(self):
        text = "話し手が変更されました"
        url = TTS_URL

        instructions = {
            "tts_speaker_change": self.person.get(),
            "tts_volume": round(self.volume.get(),2),      
            "tts_rate": round(self.rate.get(),2),          
            "tts_pitch": round(self.pitch.get(),2),         
            "tts_emphasis": round(self.emphasis.get(),2),    
            "tts_emo_joy": round(self.joy.get(),2),      
            "tts_emo_angry": round(self.anger.get(),2),     
            "tts_emo_sad": round(self.sadness.get(),2)     
        }

        tts.speak_async(text, instructions, url)

    def _eol_bytes(self, eol: str) -> bytes:
        v = eol.lower()
        if v == "crlf":
            return b"\r\n"
        if v == "none":
            return b""
        return b"\n"  # 既定 lf

    def _connect_tcp(self):
        try:
            self.sock = socket.create_connection((TCP_HOST, TCP_PORT), timeout=TCP_TIMEOUT)
            self.sock.settimeout(TCP_TIMEOUT)
        except Exception as e:
            self.sock = None
            self._log(f"! TCP接続失敗: {e}")

    def _close_tcp(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def _send_command(self, command: str):
        self._log(f"> {command}")
        if USE_TCP:
            if self.sock is None:
                self._connect_tcp()
                if self.sock is None:
                    self._log("! 送信中止 (接続なし)")
                    return
            try:
                self.sock.sendall(command.encode("utf-8") + self._terminator)
            except (BrokenPipeError, ConnectionResetError):
                self._log("! 接続断 -> 再接続試行")
                self._close_tcp()
                self._connect_tcp()
            except Exception as e:
                self._log(f"! 送信エラー: {e}")
            return

    def _on_close(self):
        self._close_tcp()
        self.xyz_client.stop()
        self.destroy()

    def _log(self, text: str):
        self.log.insert("end", text + "\n")
        self.log.see("end")

if __name__ == "__main__":
    app = RobotConsole()
    app.mainloop()