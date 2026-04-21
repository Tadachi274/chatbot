# interrupt_handler.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import json
import re


@dataclass
class InterruptDecision:
    da: str                 # BACKCHANNEL / AGREEMENT / REJECT / APPRECIATION / ANSWER / STATEMENT
    policy: str             # continue / stop_now / stop_after_sentence
    reaction: str           # nod / smile / none
    source: str             # rule / gpt


class InterruptHandler:
    """
    割り込み発話の判定専用クラス。
    - まずルールベースで判定
    - 判定できなければ GPT にフォールバック
    - 最終的に policy まで返す
    """

    RULE_BACKCHANNEL = {
        "はい", "うん", "ええ", "はいはい", "うんうん",
        "なるほど", "あ、はい", "あはい", "そうなんですね"
    }

    RULE_AGREEMENT = {
        "はい", "うん", "ええ", "お願いします", "大丈夫です", "結構です"
    }

    RULE_REJECT = {
        "違う", "違います", "いや", "いや違う", "違います違います",
        "ちがう", "いいえ", "違いますよ"
    }

    RULE_APPRECIATION = {
        "ありがとう", "ありがとうございます", "どうも"
    }

    def __init__(self, openai_client, model_name: str):
        self.openai_client = openai_client
        self.model_name = model_name

    def decide(
        self,
        text: str,
        current_robot_text: str = "",
        current_robot_type: str = "",
        is_last_sentence: bool = False,
    ) -> InterruptDecision:
        """
        割り込み発話を受けて、DA と policy を返す。
        """
        da = self.classify_rule(text, current_robot_text=current_robot_text,current_robot_type=current_robot_type)

        if da is not None:
            return InterruptDecision(
                da=da,
                policy=self.da_to_policy(da),
                reaction=self.da_to_reaction(da, is_last_sentence=is_last_sentence),
                source="rule",
            )

        da = self.classify_with_gpt(text=text, current_robot_text=current_robot_text,current_robot_type=current_robot_type)

        return InterruptDecision(
            da=da,
            policy=self.da_to_policy(da),
            reaction=self.da_to_reaction(da, is_last_sentence=is_last_sentence),
            source="gpt",
        )

    def classify_rule(self, text: str, current_robot_text: str = "", current_robot_type: str = "",) -> Optional[str]:
        """
        まず軽いルールベース判定。
        """
        t = self._normalize(text)
        if not t:
            return None

        if t in self.RULE_REJECT:
            return "REJECT"

        if t in self.RULE_APPRECIATION:
            return "APPRECIATION"

        # 「はい」は BACKCHANNEL と AGREEMENT の両方に見えるので、
        # ここでは会話継続寄りに扱って問題ない
        if t in self.RULE_BACKCHANNEL:
            return "BACKCHANNEL"

        if t in self.RULE_AGREEMENT:
            return "AGREEMENT"

        # かなり短い返答で、かつ質問文への返答らしければ ANSWER 寄り
        if self._looks_like_answer(t, current_robot_text,current_robot_type):
            return "ANSWER"

        return None

    def classify_with_gpt(self, text: str, current_robot_text: str = "",current_robot_type: str = "",) -> str:
        """
        迷うものだけ GPT で分類。
        出力は JSON のみを期待。
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたは接客対話中の割り込み発話を分類します。"
                    "出力は必ずJSONのみで返してください。"
                    '形式は {"da": "..."} のみです。'
                    "da は BACKCHANNEL, AGREEMENT, REJECT, APPRECIATION, ANSWER, STATEMENT "
                    "のいずれか1つのみを使ってください。"
                    "BACKCHANNEL は短い相槌。"
                    "AGREEMENT は承諾。"
                    "REJECT は否定・訂正。"
                    "APPRECIATION は感謝。"
                    "ANSWER は直前のロボットの質問への答え。"
                    "STATEMENT はそれ以外の内容発話です。"
                    "説明文、補足、Markdown、コードブロックは禁止です。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"直前のロボット発話: {current_robot_text}\n"
                    f"直前のロボット発話type: {current_robot_type}\n"
                    f"お客さんの割り込み発話: {text}"
                ),
            },
        ]

        resp = self.openai_client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0,
            max_tokens=32,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )

        raw = resp.choices[0].message.content.strip()
        data = json.loads(self._extract_json_text(raw))
        da = str(data.get("da", "")).strip().upper()

        allowed = {
            "BACKCHANNEL",
            "AGREEMENT",
            "REJECT",
            "APPRECIATION",
            "ANSWER",
            "STATEMENT",
        }
        if da not in allowed:
            return "STATEMENT"
        return da

    def da_to_policy(self, da: str) -> str:
        """
        分類結果から、話し中のポリシーに変換。
        """
        if da in {"BACKCHANNEL", "AGREEMENT", "APPRECIATION"}:
            return "continue"

        if da in {"REJECT", "STATEMENT"}:
            return "stop_now"

        if da == "ANSWER":
            return "stop_after_sentence"

        return "stop_after_sentence"

    def da_to_reaction(self, da: str, is_last_sentence: bool = False) -> str:
        """
        軽い身体反応の種類。
        """
        if da in {"BACKCHANNEL", "AGREEMENT"}:
            return "nod"
        if da == "APPRECIATION":
            return "smile"
        if da == "ANSWER" and is_last_sentence:
            return "nod"
        return "none"

    def _looks_like_answer(
        self,
        text: str,
        current_robot_text: str = "",
        current_robot_type: str = "",
    ) -> bool:
        t = text.strip()

        # まず DA/type を最優先
        if current_robot_type == "QUESTION":
            return len(t) <= 20

        return False

    def _normalize(self, text: str) -> str:
        t = (text or "").strip()
        if t.startswith("「") and t.endswith("」"):
            t = t[1:-1].strip()
        return t

    def _extract_json_text(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return text.strip()