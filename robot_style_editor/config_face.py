from pathlib import Path
from .config import BASE_DIR

SENTENCE_PAUSE_GAZE_OPTIONS = [
    {
        "id": "horizontal",
        "label": "横",
        "description": "文間で左右どちらかへランダムに視線を外します。",
        "lookaway": "horizontal_random",
    },
    {
        "id": "up",
        "label": "上",
        "description": "文間で上方向へ視線を外します。",
        "lookaway": "u",
    },
    {
        "id": "down",
        "label": "下",
        "description": "文間で下方向へ視線を外します。",
        "lookaway": "d",
    },
]

SENTENCE_PAUSE_GAZE_PRIORITY = 4
SENTENCE_PAUSE_GAZE_KEEPTIME = 800

# 既存の表情プリセットファイル
# robot_console.py が読んでいるものと同じファイルを使う
FACE_CONFIG_DIR = BASE_DIR.parent / "tts" / "command" / "config"
FACE_CONFIG_FILE = FACE_CONFIG_DIR / "face_config.txt"

# 表情軸の参考画像
FACE_AXIS_IMAGE_PATH = BASE_DIR / "assets" / "nikola_axis.jpg"

THINKING_FACE_OPTIONS = [
    {"id": "neutral", "label": "ニュートラル", "type": "neutral", "level": 1},
    {"id": "suspicion2", "label": "Suspicion2", "type": "Suspicion", "level": 2},
    {"id": "sorry2", "label": "Sorry2", "type": "sorry", "level": 2},
    {"id": "waitsmile3", "label": "WaitSmile3", "type": "WaitSmile", "level": 3},
]

THINKING_GAZE_OPTIONS = [
    {"id": "up", "label": "上", "lookaway": "u"},
    {"id": "down", "label": "下", "lookaway": "d"},
    {"id": "front", "label": "正面", "lookaway": "f"},
]

THINKING_FACE_PRIORITY = 3
THINKING_FACE_KEEPTIME = 3000
THINKING_GAZE_PRIORITY = 4
THINKING_GAZE_KEEPTIME = 1500

FACE_AXIS_NAMES = [str(i) for i in range(1, 36)]

FACE_DEFAULT_VALUES = [
    64, 64, 128, 128, 128,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 32, 128, 128, 128
]

FACE_DEFAULT_HEADER = (200, 1000, 4000)

FACE_EDITOR_VELOCITY = 2000
FACE_EDITOR_PRIORITY = 3
FACE_EDITOR_KEEPTIME = 3000

FACE_AXIS_DESCRIPTIONS = {
    "1": "左目の上瞼の開き度合い",
    "2": "右目の上瞼の開き度合い",
    "3": "左目の向く方向",
    "4": "右目の向く方向",
    "5": "目の位置上下",
    "6": "左目の下瞼",
    "7": "右目の下瞼",
    "8": "左眉左上げ",
    "9": "左眉左下げ",
    "10": "左眉右側",
    "11": "左 眉間",
    "12": "右眉右側上げ",
    "13": "右眉右側下げ",
    "14": "右眉左側上げ",
    "15": "右 眉間",
    "16": "左口角",
    "17": "右口角",
    "18": "左頬横",
    "19": "左頬下",
    "20": "左頬？",
    "21": "左頬下の方",
    "22": "右頬横",
    "23": "右頬下",
    "24": "右頬？",
    "25": "左頬下の方",
    "26": "上唇の尖り",
    "27": "下唇の尖り",
    "28": "上唇上",
    "29": "下唇下",
    "30": "鼻上",
    "31": "？",
    "32": "口の開き度合い",
    "33": "首の角度横",
    "34": "首の角度縦",
    "35": "首の角度回転",
}

# 聞き手の表情プリセット
LISTENING_FACE_OPTIONS = [
    {
        "id": "neutral",
        "label": "ニュートラル",
        "type": "neutral",
        "level": 1,
    },
    {
        "id": "affiliative_smile",
        "label": "親しみの笑顔",
        "type": "AffiliativeSmile",
        "level": 2,
    },
    {
        "id": "wait_smile",
        "label": "待機の笑顔",
        "type": "WaitSmile",
        "level": 2,
    },
]

LISTENING_FACE_PRIORITY = 3
LISTENING_FACE_KEEPTIME = 3000

LISTENING_EYE_AXIS_GROUPS = {
    "left": {
        "label": "左目",
        "upper_axis": "1",
        "lower_axis": "6",
    },
    "right": {
        "label": "右目",
        "upper_axis": "2",
        "lower_axis": "7",
    },
}

LISTENING_EYE_OPEN_DEFAULTS = {
    "normal": {
        "id": "normal",
        "label": "普通",
        "left_upper": 64,
        "left_lower": 0,
        "right_upper": 64,
        "right_lower": 0,
    },
    "open": {
        "id": "open",
        "label": "開く",
        "left_upper": 95,
        "left_lower": 0,
        "right_upper": 95,
        "right_lower": 0,
    },
}

LISTENING_NOD_OPTIONS = [
    {
        "id": "none",
        "label": "無",
        "amplitude": 0,
        "duration": 0,
    },
    {
        "id": "small",
        "label": "小",
        "amplitude": 7,
        "duration": 300,
    },
    {
        "id": "middle",
        "label": "中",
        "amplitude": 10,
        "duration": 400,
    },
    {
        "id": "large",
        "label": "大",
        "amplitude": 15,
        "duration": 500,
    },
]

LISTENING_NOD_PRIORITY = 3
LISTENING_NOD_TIME = 1

LISTENING_BACKCHANNEL_WORDS = ["うん", "はい", "ええ"]

LISTENING_BACKCHANNEL_AMOUNT_OPTIONS = [
    {
        "id": "few",
        "label": "少ない",
        "silence_sec": 0.4,
        "description": "長めの沈黙で相槌を入れる",
    },
    {
        "id": "middle",
        "label": "中",
        "silence_sec": 0.2,
        "description": "自然な文節の間で相槌を入れる",
    },
    {
        "id": "many",
        "label": "多い",
        "silence_sec": 0.1,
        "description": "短い沈黙でも相槌を入れる",
    },
]

LISTENING_BACKCHANNEL_VOICE_MODE_OPTIONS = [
    {
        "id": "always",
        "label": "毎回",
        "description": "うなづきのたびに音声相槌を入れます。",
    },
    {
        "id": "sometimes",
        "label": "たまに",
        "description": "うなづきの一部だけ音声相槌を入れます。",
    },
    {
        "id": "none",
        "label": "全くなし",
        "description": "うなづきだけ行い、音声相槌は入れません。",
    },
]

LISTENING_BACKCHANNEL_VOICE_PROBABILITY_DEFAULT = 0.4
LISTENING_BACKCHANNEL_SILENCE_HOLD_SEC_DEFAULT = 0.60
LISTENING_BACKCHANNEL_START_HOLD_SEC_DEFAULT = 0.08

LISTENING_BACKCHANNEL_WORD_OPTIONS = [
    {
        "id": "un",
        "label": "うん",
        "text": "うん",
        "type": "wav",
        "wav_path": BASE_DIR / "sample_audio" / "うん.wav",
    },
    {
        "id": "hai",
        "label": "はい",
        "text": "はい",
        "type": "wav",
        "wav_path": BASE_DIR / "sample_audio" / "はい.wav",
    },
    {
        "id": "ee",
        "label": "ええ",
        "text": "ええ",
        "type": "wav",
        "wav_path": BASE_DIR / "sample_audio" / "ええ.wav",
    },
    {
        "id": "other",
        "label": "その他",
        "text": "",
        "type": "tts",
        "wav_path": None,
    },
]

UNDERSTANDING_FACE_OPTIONS = [
    {
        "id": "neutral",
        "label": "ニュートラル",
        "type": "neutral",
        "level": 1,
    },
    {
        "id": "reward_smile3",
        "label": "RewardSmile3",
        "type": "RewardSmile",
        "level": 3,
    },
    {
        "id": "positive_surprise2",
        "label": "PositiveSurprise2",
        "type": "PositiveSurprise",
        "level": 2,
    },
]

UNDERSTANDING_FACE_PRIORITY = 3
UNDERSTANDING_FACE_KEEPTIME = 3000

UNDERSTANDING_NOD_OPTIONS = [
    {
        "id": "large_once",
        "label": "大 1回",
        "amplitude": 15,
        "duration": 500,
        "count": 1,
    },
    {
        "id": "large_twice",
        "label": "大 2回",
        "amplitude": 15,
        "duration": 500,
        "count": 2,
    },
]

UNDERSTANDING_NOD_PRIORITY = 3
UNDERSTANDING_NOD_INTERVAL_SEC = 0.25

UNDERSTANDING_WORD_OPTIONS = [
    {
        "id": "hai",
        "label": "はい",
        "text": "はい",
        "type": "wav",
        "wav_path": BASE_DIR / "sample_audio" / "はい.wav",
    },
    {
        "id": "un",
        "label": "うん",
        "text": "うん",
        "type": "wav",
        "wav_path": BASE_DIR / "sample_audio" / "うん.wav",
    },
    {
        "id": "accepted",
        "label": "承知いたしました",
        "text": "承知いたしました",
        "type": "wav",
        "wav_path": BASE_DIR / "sample_audio" / "承知いたしました.wav",
    },
    {
        "id": "naruhodo",
        "label": "なるほど",
        "text": "なるほど",
        "type": "wav",
        "wav_path": BASE_DIR / "sample_audio" / "なるほど.wav",
    },
    {
        "id": "sounandesune",
        "label": "そうなんですね",
        "text": "そうなんですね",
        "type": "wav",
        "wav_path": BASE_DIR / "sample_audio" / "そうなんですね.wav",
    },
    {
        "id": "other",
        "label": "その他",
        "text": "",
        "type": "tts",
        "wav_path": None,
    },
]

UNDERSTANDING_SAMPLE_TEXT = "今日から３日間沖縄で旅行しようと思っています"
UNDERSTANDING_RESPONSE_DELAY_FALLBACK_SEC = 0.2