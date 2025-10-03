import os
import json
from pathlib import Path
from datetime import datetime
from openai import OpenAI  # tts_voicevoxからtts_openaiに変更
import test_chatbot as chatbot
import compiler_openai
import string_to_file
import sys
from dotenv import load_dotenv
 
CONFIG_PATH = "voice_config_openai.json"
TTS_SERVER = "openai"  # Assuming this is the TTS server you want to use

# ---------- OpenAI API 設定 ----------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("環境変数 OPENAI_API_KEY が設定されていません。")
client = OpenAI(api_key=api_key)
MODEL = "gpt-4o-mini"

# ---------- OpenAI Function 定義 ----------
content = """
    あなたは話し方をカスタマイズするシステムに命令を出すシステムです。
    ある人の要望を受け取り、カスタマイズするシステムが理解しやすいように要望を具体化して詳細化してください。   
    カスタマイズするシステムはその詳細な要望を受け取り、話し方を変更させます。
    例えば、高齢者の「会話しやすいトーンで話して」という要望に対しては、
    声の調子について、
    ・声のトーンを少し上げ明るい調子で話す
    ・スピードを少しゆっくりにして相手が聞き取りやすいようにする
    ・会話と会話の間を少しあけ相手に理解する時間を作る
    などと話し方の何を何のために変えるか具体化と詳細化してください。
    ここでは声の調子しかあげていませんが、話す内容を変化させた方が良い場合は、それについても記載してください。
    他の例だと「分からなそうだったら分かるように言って」という要望に対しては、
    ### 話し方のカスタマイズ指示（例：高齢者向け「会話しやすいトーン」）

    ### 1\. 相手の理解状況の確認

    *   **相手の反応を観察する**：返答が遅い、表情や声が曖昧、返事が「うん」だけ、などの場合に「分かっていないかも」と判断する。
    *   **確認の声かけ**：「ここまでで大丈夫ですか？」「ちょっと分かりにくかったですか？」など理解度を確認する質問を入れる。

    ### 2\. 言葉の選び直し（分かりやすく言い換える）

    *   **専門用語や難語を避ける**：可能であれば平易な言葉に言い換える（例：「データベース」→「情報をまとめて入れておく箱」）。
    *   **短い文に分ける**：一度に多くを説明せず、区切って順序立てる。
    *   **具体例を使う**：抽象的な説明だけでなく、身近な例を追加する。

    ### 3\. 話す調子の調整

    *   **声のスピード**：理解しにくそうな場面では、少しゆっくりめにする。
    *   **間の取り方**：説明後に短い間を空けて、質問や反応を待つ。
    *   **強調**：大事な部分は声を少し強めにする、または言葉を繰り返す。

    ### 4\. 補助的な工夫

    *   **別の表現をすぐ用意する**：「つまり〜」「言い換えると〜」と自然にリフレーズする。
    *   **確認しながら進める**：「分かりやすいですか？」「もう少し説明した方がいいですか？」と段階的に確かめる。
    *   **図やジェスチャーを併用**（音声だけでなければ）：視覚的に補強すると理解度が高まりやすい。
    としてください。
    そして、要望を具体化して詳細化したものを返してください。それ以外の必要のない情報は絶対に一切含めないでください。
"""

def compile(user_request: str) -> str:
    messages = [
        {"role": "system", "content": content},
        {"role": "user", "content": user_request}
    ]
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )
    return response.choices[0].message.content
