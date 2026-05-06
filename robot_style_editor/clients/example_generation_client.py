import json
import os
import urllib.error
import urllib.request


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
EXAMPLE_GENERATION_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")


class ExampleGenerationClient:
    def __init__(self, api_key=None, model=None, timeout=90):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model or EXAMPLE_GENERATION_MODEL
        self.timeout = timeout

    def generate_scene(self, scene, profile, global_request=""):
        self._require_api_key()
        payload = self._build_payload(
            input_text=self._build_scene_prompt(scene, profile, global_request),
            schema=self._scene_schema(),
        )
        data = self._request(payload)
        return self._parse_json_output(data)

    def revise_scene(self, scene, profile, current_dialogue, global_request):
        self._require_api_key()
        payload = self._build_payload(
            input_text=self._build_revision_prompt(
                scene=scene,
                profile=profile,
                current_dialogue=current_dialogue,
                global_request=global_request,
            ),
            schema=self._scene_schema(),
        )
        data = self._request(payload)
        return self._parse_json_output(data)

    def revise_turn(self, scene, profile, current_dialogue, turn_index, turn_request):
        self._require_api_key()
        payload = self._build_payload(
            input_text=self._build_turn_revision_prompt(
                scene=scene,
                profile=profile,
                current_dialogue=current_dialogue,
                turn_index=turn_index,
                turn_request=turn_request,
            ),
            schema=self._turn_schema(),
        )
        data = self._request(payload)
        return self._parse_json_output(data)

    def _require_api_key(self):
        if not self.api_key:
            self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY が設定されていません。")

    def _build_payload(self, input_text, schema):
        return {
            "model": self.model,
            "instructions": (
                "あなたは日本語接客会話の調整者です。"
                "ロボットの話し方設定を厳密に反映し、自然な会話だけをJSONで返してください。"
                "客の発話は原則変更しません。店員/スタッフの発話だけを調整します。"
            ),
            "input": input_text,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema["name"],
                    "strict": True,
                    "schema": schema["schema"],
                }
            },
        }

    def _request(self, payload):
        req = urllib.request.Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                return json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API error: {e.code} {body}") from e

    def _parse_json_output(self, data):
        if data.get("output_text"):
            return json.loads(data["output_text"])

        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return json.loads(content.get("text", "{}"))

        raise RuntimeError("OpenAI API の応答からJSON本文を取得できませんでした。")

    def _build_scene_prompt(self, scene, profile, global_request):
        return json.dumps(
            {
                "task": "現在のロボット話し方設定に合わせて、接客場面の会話を生成してください。",
                "rules": self._generation_rules(),
                "profile": profile,
                "scene": self._compact_scene(scene),
                "global_request": global_request,
            },
            ensure_ascii=False,
            indent=2,
        )

    def _build_revision_prompt(self, scene, profile, current_dialogue, global_request):
        return json.dumps(
            {
                "task": "現在表示中の会話を、全体要望に合わせて全体的に再生成してください。",
                "rules": self._generation_rules(),
                "profile": profile,
                "scene": self._compact_scene(scene),
                "current_dialogue": current_dialogue,
                "global_request": global_request,
            },
            ensure_ascii=False,
            indent=2,
        )

    def _build_turn_revision_prompt(self, scene, profile, current_dialogue, turn_index, turn_request):
        return json.dumps(
            {
                "task": "指定された店員/スタッフ発話だけを修正してください。他のturnは変更しません。",
                "rules": self._generation_rules(),
                "profile": profile,
                "scene": self._compact_scene(scene),
                "current_dialogue": current_dialogue,
                "target_turn_index": turn_index,
                "turn_request": turn_request,
            },
            ensure_ascii=False,
            indent=2,
        )

    def _compact_scene(self, scene):
        return {
            "id": scene["id"],
            "venue": scene["venue"],
            "title": scene["title"],
            "turns": [
                {
                    "role": turn["role"],
                    "text": turn.get("text", turn.get("base_text", "")),
                    "intent_parts": turn.get("intent_parts", []),
                }
                for turn in scene["turns"]
            ],
        }

    def _generation_rules(self):
        return [
            "敬語、親しみ、語彙、長さを必ず反映する。",
            "挨拶、説明、質問、承諾、要求、謝罪、感謝、雑談、フィラーの各設定とテクニックを反映する。",
            "フィラー設定が有効な場合だけ、profile.filler.phrases から短いフィラーを選び、相談・質問への返答など考えを挟むのが自然な箇所にだけ入れる。",
            "フィラーを入れる場合は、発話文にも含め、intent_parts には intent=filler の短いまとまりとして分ける。",
            "フィラー設定が無効な場合、または greeting/apology/gratitude/acceptance/request が中心の発話では、フィラーを入れない。",
            "長さが短い場合は要点だけにし、長い場合は自然な補足を加える。",
            "profile.style_detail はDAごとのテクニックより上位の全体方針として扱い、情報構造、情報量、感情表出、対人的配慮、主導性を全ての店員/スタッフ発話に自然に反映する。",
            "profile.style_detail.prompt に含まれる指示は、各DAの技法と衝突しない範囲で優先して反映する。",
            "profile.special_consideration.text が空でない場合、これは強い制約として扱う。店員/スタッフ発話ではこの条件に反する表現や提案を避け、可能な限り明示的に配慮する。",
            "profile.special_consideration と場面事実が衝突する場合は、場面事実を変えずに、表現・提案・説明方法で配慮する。",
            "カジュアル設定では敬語を使いすぎない。",
            "話者は profile.speaker_person を最優先して判断する。",
            "話者がのぞみの場合、敬語がカジュアルでも「っす」「っすか」「っすね」を絶対に使わない。",
            "話者がのぞみでカジュアルな場合は、「だよ」「かな」「ね」など柔らかい語尾にする。",
            "話者がけんたの場合だけ、親しみ高で接客として許容できる範囲の「っす」系を使ってよい。",
            "intent_partsの意図は、後で声色・表情・お辞儀を割り当てるため維持する。",
            "店員/スタッフ発話は、文または意味のまとまりごとにintent_partsへ分割する。",
            "intent_partsのintentは greeting, explanation, question, acceptance, request, apology, gratitude, smalltalk, filler のいずれかを優先する。",
            "客の発話は変更しない。",
            "場面の意味、商品名、金額、部屋番号などの事実は変えない。",
            "不自然なテクニックの積み上げを避け、1つの自然な店員発話としてまとめる。",
        ]

    def _scene_schema(self):
        return {
            "name": "generated_customer_service_scene",
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["turns", "summary"],
                "properties": {
                    "summary": {"type": "string"},
                    "turns": {
                        "type": "array",
                        "items": self._turn_schema_object(),
                    },
                },
            },
        }

    def _turn_schema(self):
        return {
            "name": "generated_customer_service_turn",
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["turn", "reason"],
                "properties": {
                    "turn": self._turn_schema_object(),
                    "reason": {"type": "string"},
                },
            },
        }

    def _turn_schema_object(self):
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["role", "text", "intent_parts"],
            "properties": {
                "role": {"type": "string", "enum": ["customer", "staff"]},
                "text": {"type": "string"},
                "intent_parts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["intent", "text"],
                        "properties": {
                            "intent": {"type": "string"},
                            "text": {"type": "string"},
                        },
                    },
                },
            },
        }
