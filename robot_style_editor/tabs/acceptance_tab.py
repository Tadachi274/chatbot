from ..config_face import (
    ACCEPTANCE_FACE_KEEPTIME,
    ACCEPTANCE_FACE_OPTIONS,
    ACCEPTANCE_FACE_PRIORITY,
)
from ..config_intention import ACCEPTANCE_DEFAULT_TEXT, ACCEPTANCE_VOICE_PRESETS
from .simple_intent_tab import SimpleIntentTab


ACCEPTANCE_TEXT_VARIANTS = {
    "very_formal": {
        "easy": {
            "short": "かしこまりました。",
            "middle": "かしこまりました。承ります。",
            "long": "かしこまりました。内容を確認のうえ、こちらで承ります。",
        },
        "middle": {
            "short": "かしこまりました。",
            "middle": "かしこまりました。承ります。",
            "long": "かしこまりました。内容を確認のうえ、こちらで対応いたします。",
        },
        "hard": {
            "short": "承知いたしました。",
            "middle": "承知いたしました。こちらで承ります。",
            "long": "承知いたしました。内容を確認のうえ、こちらで対応いたします。",
        },
    },
    "formal": {
        "easy": {
            "short": "かしこまりました。",
            "middle": "かしこまりました。対応します。",
            "long": "かしこまりました。確認して、こちらで対応します。",
        },
        "middle": {
            "short": "承知しました。",
            "middle": "承知しました。こちらで対応します。",
            "long": "承知しました。内容を確認して、こちらで対応します。",
        },
        "hard": {
            "short": "承知しました。",
            "middle": "承知しました。こちらで対応いたします。",
            "long": "承知しました。内容を確認のうえ、こちらで対応いたします。",
        },
    },
    "polite": {
        "easy": {
            "short": "わかりました。",
            "middle": "わかりました。対応します。",
            "long": "わかりました。確認して、こちらで対応します。",
        },
        "middle": {
            "short": "承知しました。",
            "middle": "承知しました。こちらで対応します。",
            "long": "承知しました。内容を確認して、こちらで対応します。",
        },
        "hard": {
            "short": "承知しました。",
            "middle": "承知しました。対応いたします。",
            "long": "承知しました。内容を確認のうえ、対応いたします。",
        },
    },
    "casual": {
        "easy": {
            "short": "わかった。",
            "middle": "わかった。やっておくね。",
            "long": "わかった。確認して、こっちでやっておくね。",
        },
        "middle": {
            "short": "了解。",
            "middle": "了解。対応するね。",
            "long": "了解。内容を確認して、こっちで対応するね。",
        },
        "hard": {
            "short": "了解。",
            "middle": "了解。こちらで対応するね。",
            "long": "了解。内容を確認して、こちらで対応するね。",
        },
    },
}


class AcceptanceTab(SimpleIntentTab):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(
            parent,
            profile_store=profile_store,
            tts_client=tts_client,
            status_var=status_var,
            intent_key="acceptance",
            intent_label="承諾時",
            page_title="承諾時の話し方を選ぶ",
            description="相手の依頼や発言を受け入れるときの本文、表情、声色を調整します。",
            text_title="承諾文",
            default_text=ACCEPTANCE_DEFAULT_TEXT,
            text_variants=ACCEPTANCE_TEXT_VARIANTS,
            face_options=ACCEPTANCE_FACE_OPTIONS,
            face_priority=ACCEPTANCE_FACE_PRIORITY,
            face_keeptime=ACCEPTANCE_FACE_KEEPTIME,
            voice_presets=ACCEPTANCE_VOICE_PRESETS,
            on_saved=on_saved,
        )
