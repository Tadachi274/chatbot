from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SAVE_DIR = BASE_DIR / "save_json"
DEFAULT_SCENARIO_PATH = SAVE_DIR / "conversation_scenario.json"

SCENARIO_OPTIONS = [
    {
        "id": "luxury_hotel",
        "label": "高級ホテル",
        "default_title": "高級ホテルの接客",
    },
    {
        "id": "izakaya",
        "label": "居酒屋",
        "default_title": "居酒屋の接客",
    },
    {
        "id": "aeon_information",
        "label": "イオンのインフォメーションセンター",
        "default_title": "イオンのインフォメーションセンターの接客",
    },
]

CONVERSATION_SCENE_OPTIONS_BY_SCENARIO = {
    "luxury_hotel": [
        {
            "id": "hotel_checkin",
            "label": "手続き系: チェックイン",
            "intent": "explanation",
        },
        {
            "id": "hotel_dirty_bed",
            "label": "謝罪系: ベッドが汚れていた",
            "intent": "apology",
        },
        {
            "id": "hotel_checkout",
            "label": "感謝系: チェックアウト",
            "intent": "gratitude",
        },
        {
            "id": "hotel_sightseeing",
            "label": "質問系: 近くの観光スポット",
            "intent": "question",
        },
    ],
    "izakaya": [
        {
            "id": "izakaya_order",
            "label": "手続き系: 注文を取る",
            "intent": "explanation",
        },
        {
            "id": "izakaya_wrong_order",
            "label": "謝罪系: 注文と違う料理が出た",
            "intent": "apology",
        },
        {
            "id": "izakaya_checkout",
            "label": "感謝系: 会計とお見送り",
            "intent": "gratitude",
        },
        {
            "id": "izakaya_recommendation",
            "label": "質問系: おすすめメニューを聞く",
            "intent": "question",
        },
    ],
    "aeon_information": [
        {
            "id": "aeon_floor_guide",
            "label": "案内系: 売り場を案内する",
            "intent": "explanation",
        },
        {
            "id": "aeon_lost_item",
            "label": "謝罪系: 落とし物が見つからない",
            "intent": "apology",
        },
        {
            "id": "aeon_help_thanks",
            "label": "感謝系: 案内後のお礼",
            "intent": "gratitude",
        },
        {
            "id": "aeon_event_question",
            "label": "質問系: イベント場所を聞く",
            "intent": "question",
        },
    ],
}


def conversation_scene_options(scenario_id):
    return CONVERSATION_SCENE_OPTIONS_BY_SCENARIO.get(
        scenario_id,
        CONVERSATION_SCENE_OPTIONS_BY_SCENARIO["luxury_hotel"],
    )

DEFAULT_UTTERANCE_DURATION = 3.0
DEFAULT_PAUSE_DURATION = 0.8
DEFAULT_SENTENCE_DURATION = 1.8
MIN_EVENT_TIME = 0.0
TIME_RESOLUTION = 0.1
TIMELINE_PIXELS_PER_SECOND = 110
TIMELINE_MIN_SECONDS = 5

FACE_AXIS_RANGE = (0, 255)
FACE_AXIS_VELOCITY = 2000
FACE_AXIS_PRIORITY = 3
FACE_AXIS_KEEPTIME = 3000

FACE_AXIS_DEFAULT_VALUES = {
    "1": 64,
    "2": 64,
    "3": 128,
    "4": 128,
    "5": 128,
    "6": 0,
    "7": 0,
    "8": 0,
    "9": 0,
    "10": 0,
    "11": 0,
    "12": 0,
    "13": 0,
    "14": 0,
    "15": 0,
    "16": 0,
    "17": 0,
    "18": 0,
    "19": 0,
    "20": 0,
    "21": 0,
    "22": 0,
    "23": 0,
    "24": 0,
    "25": 0,
    "26": 0,
    "27": 0,
    "28": 0,
    "29": 0,
    "30": 0,
    "31": 0,
    "32": 32,
    "33": 128,
    "34": 128,
    "35": 128,
}

FACE_AXIS_LABELS = {
    "1": "左上瞼",
    "2": "右上瞼",
    "3": "左目の向き",
    "4": "右目の向き",
    "5": "目の上下位置",
    "6": "左下瞼",
    "7": "右下瞼",
    "8": "左眉左側",
    "9": "左眉左下げ",
    "10": "左眉右側",
    "11": "左眉間",
    "12": "右眉右側",
    "13": "右眉右下げ",
    "14": "右眉左側",
    "15": "右眉間",
    "16": "左口角",
    "17": "右口角",
    "18": "左頬横",
    "19": "左頬下",
    "20": "左頬",
    "21": "左頬下方",
    "22": "右頬横",
    "23": "右頬下",
    "24": "右頬",
    "25": "右頬下方",
    "26": "上唇の尖り",
    "27": "下唇の尖り",
    "28": "上唇上",
    "29": "下唇下",
    "30": "鼻上",
    "31": "未確認軸",
    "32": "口の開き",
    "33": "首 横",
    "34": "首 縦",
    "35": "首 回転",
}

FACE_EXPRESSION_DEFINITIONS = {
    "emotion_neutral": {
        "label": "ニュートラル",
        "groups": [],
        "command": {
            "type": "emotion",
            "emotion": "neutral",
            "text": "/emotion neutral",
        },
    },
    "smile": {
        "label": "笑顔",
        "groups": [
            {
                "id": "upper_eyelids",
                "label": "左右の上瞼",
                "mode": "symmetric",
                "axes": ["1", "2"],
                "default": 78,
            },
            {
                "id": "mouth_corners",
                "label": "左右の口角",
                "mode": "symmetric",
                "axes": ["16", "17"],
                "default": 85,
            },
            {
                "id": "mouth_open",
                "label": "口の開き",
                "mode": "single",
                "axes": ["32"],
                "default": 36,
            },
        ],
    },
    "neutral": {
        "label": "通常",
        "groups": [
            {
                "id": "upper_eyelids",
                "label": "左右の上瞼",
                "mode": "symmetric",
                "axes": ["1", "2"],
                "default": 64,
            },
            {
                "id": "mouth_corners",
                "label": "左右の口角",
                "mode": "symmetric",
                "axes": ["16", "17"],
                "default": 0,
            },
        ],
    },
    "troubled": {
        "label": "困り",
        "groups": [
            {
                "id": "brows_inner",
                "label": "左右の眉間",
                "mode": "symmetric",
                "axes": ["11", "15"],
                "default": 55,
            },
            {
                "id": "mouth_corners",
                "label": "左右の口角",
                "mode": "symmetric",
                "axes": ["16", "17"],
                "default": 0,
            },
        ],
    },
    "surprised": {
        "label": "驚き",
        "groups": [
            {
                "id": "upper_eyelids",
                "label": "左右の上瞼",
                "mode": "symmetric",
                "axes": ["1", "2"],
                "default": 110,
            },
            {
                "id": "mouth_open",
                "label": "口の開き",
                "mode": "single",
                "axes": ["32"],
                "default": 95,
            },
        ],
    },
}

FACE_EXPRESSION_OPTIONS = [
    definition["label"]
    for definition in FACE_EXPRESSION_DEFINITIONS.values()
]

SPEAKER_STAFF = "staff"
SPEAKER_CUSTOMER = "customer"

SPEAKER_LABELS = {
    SPEAKER_STAFF: "店員発話",
    SPEAKER_CUSTOMER: "客発話",
}

STAFF_EVENT_LANES = [
    {
        "id": "face",
        "label": "表情",
        "options": FACE_EXPRESSION_OPTIONS,
        "default": "笑顔",
    },
    {
        "id": "gaze",
        "label": "視線",
        "options": [
            "客の方",
            "上",
            "下",
            "右",
            "左",
            "右上",
            "左上",
            "右下",
            "左下",
            "正面",
        ],
        "default": "客の方",
    },
    {
        "id": "nod",
        "label": "頷き",
        "options": ["小さく", "普通", "深く", "お辞儀", "その他"],
        "default": "お辞儀",
    },
]

LANE_BY_ID = {lane["id"]: lane for lane in STAFF_EVENT_LANES}

VOICE_FRIENDLY_MAP = {
    "volume": (1.3, 1.3),
    "rate": (1.0, 1.0),
    "pitch": (1.0, 1.05),
    "emphasis": (1.0, 1.05),
    "joy": (0.0, 0.4),
    "anger": (0.0, 0.0),
    "sadness": (0.0, 0.4),
}

VOICE_CALM_MAP = {
    "volume": (1.3, 1.3),
    "rate": (1.0, 1.0),
    "pitch": (1.0, 0.95),
    "emphasis": (1.0, 0.95),
    "joy": (0.0, 0.1),
    "anger": (0.0, 0.0),
    "sadness": (0.0, 0.4),
}

VOICE_TENSION_MAP = {
    "volume": (1.3, 1.3),
    "rate": (1.0, 1.1),
    "pitch": (1.0, 1.1),
    "emphasis": (1.0, 1.4),
    "joy": (0.0, 0.4),
    "anger": (0.0, 0.35),
    "sadness": (0.0, 0.0),
}

VOICE_BASE_PARAMS = {
    "volume": 1.3,
    "rate": 1.0,
    "pitch": 1.0,
    "emphasis": 1.0,
    "joy": 0.0,
    "anger": 0.0,
    "sadness": 0.0,
}

VOICE_RANGE = {
    "volume": (0.0, 2.0),
    "rate": (0.5, 2.0),
    "pitch": (0.5, 2.0),
    "emphasis": (0.0, 2.0),
    "joy": (0.0, 1.0),
    "anger": (0.0, 1.0),
    "sadness": (0.0, 1.0),
}

VOICE_CONTROL_RANGE = (0.0, 2.0)


def clamp(value, vmin, vmax):
    return max(vmin, min(value, vmax))


def add_voice_modifier(params, control_value, mapping):
    for key, (base, target) in mapping.items():
        delta = target - base
        ratio = (float(control_value) - 1.0) / (1.5 - 1.0)
        params[key] += delta * ratio

    return params


def compute_voice_params(friendly=1.0, calm=1.0, tension=1.0):
    params = dict(VOICE_BASE_PARAMS)
    params = add_voice_modifier(params, friendly, VOICE_FRIENDLY_MAP)
    params = add_voice_modifier(params, calm, VOICE_CALM_MAP)
    params = add_voice_modifier(params, tension, VOICE_TENSION_MAP)

    for key, (vmin, vmax) in VOICE_RANGE.items():
        params[key] = round(clamp(params[key], vmin, vmax), 2)

    return params


def voice_params_to_tts_instructions(params):
    return {
        "tts_volume": round(float(params["volume"]), 2),
        "tts_rate": round(float(params["rate"]), 2),
        "tts_pitch": round(float(params["pitch"]), 2),
        "tts_emphasis": round(float(params["emphasis"]), 2),
        "tts_emo_joy": round(float(params["joy"]), 2),
        "tts_emo_angry": round(float(params["anger"]), 2),
        "tts_emo_sad": round(float(params["sadness"]), 2),
    }


def default_voice_data():
    return {
        "controls": {
            "friendly": 1.0,
            "calm": 1.0,
            "tension": 1.0,
        },
        "params": compute_voice_params(),
    }


def face_definition_by_label(label):
    for expression_id, definition in FACE_EXPRESSION_DEFINITIONS.items():
        if definition["label"] == label:
            return expression_id, definition

    expression_id = "smile"
    return expression_id, FACE_EXPRESSION_DEFINITIONS[expression_id]


def default_face_data(label="笑顔"):
    expression_id, definition = face_definition_by_label(label)
    axes = {}
    groups = []

    if definition.get("command", {}).get("type") == "emotion":
        return {
            "id": expression_id,
            "label": definition["label"],
            "groups": [],
            "axes": {},
            "command": dict(definition["command"]),
        }

    for group in definition["groups"]:
        value = int(group.get("default", 0))
        group_values = {
            axis: value
            for axis in group["axes"]
        }
        axes.update(group_values)
        groups.append(
            {
                "id": group["id"],
                "label": group["label"],
                "mode": group.get("mode", "single"),
                "axes": list(group["axes"]),
                "values": group_values,
            }
        )

    return {
        "id": expression_id,
        "label": definition["label"],
        "groups": groups,
        "axes": axes,
        "command": {
            "type": "movemulti5",
            "velocity": FACE_AXIS_VELOCITY,
            "priority": FACE_AXIS_PRIORITY,
            "keeptime": FACE_AXIS_KEEPTIME,
        },
    }


def face_axis_commands(face_data):
    command = face_data.get("command", {})
    if command.get("type") == "emotion":
        return [
            {
                "command": "/emotion",
                "emotion": command.get("emotion", "neutral"),
                "text": command.get("text", "/emotion neutral"),
            }
        ]

    velocity = int(command.get("velocity", FACE_AXIS_VELOCITY))
    priority = int(command.get("priority", FACE_AXIS_PRIORITY))
    keeptime = int(command.get("keeptime", FACE_AXIS_KEEPTIME))
    return [
        {
            "command": "/movemulti5",
            "axis": str(axis),
            "value": int(value),
            "velocity": velocity,
            "priority": priority,
            "keeptime": keeptime,
            "text": f"/movemulti5 {axis} {int(value)} {velocity} {priority} {keeptime}",
        }
        for axis, value in face_data.get("axes", {}).items()
    ]
