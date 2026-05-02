#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import logging
import openai
import os
from dotenv import load_dotenv
from pathlib import Path
import sys
import threading
import time
import json
import re

import speaking_style_file
import system_content_file
import tts_nikola as tts
from string_to_file import StringFile
import fixed_reply

from filler.asr_stream import iter_asr_events
from filler.robot_client import RobotCommandClient
from filler.filler_controller import FillerController
from interrupt_handler import InterruptHandler
from command.xyz_server import XYZClient
import utterance_planner as ut

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

HOST = os.getenv("HOST", "192.168.0.165")
PORT = int(os.getenv("PORT", 8888))
OPENAI_MODEL = "gpt-5-chat-latest"
tts_url = 'http://192.168.0.169:15001/synthesize'
CONFIG_PATH_PROMPT = "voice_config_openai.json"
CONFIG_PATH_TTS = "command/voice_state_emo.json"
CONFIG_PATH_MOTION = "command/motion_state.json"

MAX_TURNS = 3  # 直近3往復を保持
SCENARIO = "hotel" # "hotel" "market" "electronics_store" "restaurant"
STSTEM_CONTENT = getattr(system_content_file, SCENARIO)


def start_tick_thread(controller: FillerController):
    def _loop():
        while True:
            controller.tick()
            time.sleep(0.5)
    th = threading.Thread(target=_loop, daemon=True)
    th.start()


def remove_quotes(text):
    if text.startswith('「') and text.endswith('」'):
        return text[1:-1]
    return text

def guess_near_end_sec(sent: str) -> float:
    n = len(sent)
    if n <= 8:
        return 0.4
    if n <= 20:
        return 0.7
    return 1.0


DA_TYPES = {
        "OPENING",
        "STATEMENT",
        "OPINION",
        "QUESTION",
        "APOLOGY",
        "THANKING",
        "CLOSING",
        "ACCEPT",
    }

def extract_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()

def parse_reply_json(raw_text: str) -> list[dict]:
    raw_text = extract_json_text(raw_text)
    data = json.loads(raw_text)

    if not isinstance(data, list):
        raise ValueError("reply JSON must be a list")

    parsed = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"item {i} must be dict")

        utterance = item.get("utterance")
        da_type = item.get("type")

        if not isinstance(utterance, str) or not utterance.strip():
            raise ValueError(f"item {i} utterance is invalid")
        if da_type not in DA_TYPES:
            raise ValueError(f"item {i} type is invalid: {da_type}")

        parsed.append({
            "utterance": utterance.strip(),
            "type": da_type
        })

    if not parsed:
        raise ValueError("reply JSON is empty")

    return parsed

def reply_json_to_text(reply_items: list[dict]) -> str:
    return "".join(item["utterance"] for item in reply_items)

def normalize_history_assistant_content(reply_items: list[dict]) -> str:
    return json.dumps(reply_items, ensure_ascii=False)


class StyleChangeServer(object):
    def __init__(self, port=13204):
        self.addFile = StringFile(1)
        self.history = []   # [{"user": ..., "assistant": ...}, ...]
        self.is_speaking = False
        self.lock = threading.Lock()
        self.last_style_mtime = None
        self.cached_style_prompt = ""
        self.prefetch_reply = None
        self.interrupt_handler = InterruptHandler(
            openai_client=openai,
            model_name=OPENAI_MODEL,
        )
        self.current_prepared = []
        self.current_sentence_index = -1
        self.stop_requested = False
        self.stop_after_sentence = False
        self.opening_prefetch = {}
        self.skip_next_final_text = None

    def load_prompt_config(self):
        system_content = STSTEM_CONTENT
        system_content2 = self.refresh_style_prompt_if_needed()
        return system_content, system_content2

    def build_base_messages(self):
        system_content, system_content2 = self.load_prompt_config()

        if SCENARIO == "hotel":
            system_content2 = system_content2 + """
        CLOSING はチェックイン手続き完了後の締めの案内として使ってください。
        具体的には以下のような内容がCLOSINGに含まれます：
        ・お部屋への案内（例：「それではお部屋までご案内いたします」）
        CLOSING を使う場合は、必ず『チェックインが完了した文脈』でのみ使用してください。
        それ以外の場面では CLOSING を使ってはいけません。"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "system", "content": f"話し方の要望は以下の通りです。{system_content2}"}
        ]

        return messages

    def refresh_style_prompt_if_needed(self):
        style_path = speaking_style_file.STYLE_STATE_PATH  
        try:
            mtime = style_path.stat().st_mtime if style_path.exists() else None

            if mtime != self.last_style_mtime or self.cached_style_prompt is None:
                self.cached_style_prompt = speaking_style_file.build_prompt()
                self.last_style_mtime = mtime
                print("[Chatbot_refresh] speaking_style_state.json updated -> system_content2 refreshed")
        except Exception as e:
            print(f"[Chatbot_refrech] style refresh error: {e}")
        
        return self.cached_style_prompt

    def append_recent_history(self, messages):
        recent = self.history[-MAX_TURNS:]
        for turn in recent:
            if turn.get("user"):
                messages.append({"role": "user", "content": f"「{turn['user']}」"})
            if turn.get("assistant"):
                messages.append({"role": "assistant", "content": turn["assistant"]})
        return messages
    
   
    

#### ----- 行動や発言を制御　-----　####
    ###  話す関数
    def speak_text(self, text, filler=None):
        print(f"[Chatbot] Send at {datetime.now()}: {text}\n")

        if filler is not None:
            filler.on_gpt_done_before_tts()

        try:
            self.is_speaking = True
            th, done_event = tts.speak_async(
                text,
                config_path=CONFIG_PATH_TTS,
                url=tts_url,
                near_end_sec=2.0,
                near_end_callback=(filler.on_tts_near_end if filler is not None else None),
            )

            def _wait_tts_done():
                done_event.wait()
                self.is_speaking = False
                if filler is not None:
                    filler.on_tts_done_after_playback()
                print("[Chatbot] TTS playback done")

            threading.Thread(target=_wait_tts_done, daemon=True).start()

        except Exception as e:
            self.is_speaking = False
            logging.warning(f"TTS error: {e}")

    ### 文章を計画し、再生する関数
    def speak_text_planned(self, text, filler=None):
        print(f"[Chatbot] Send at {datetime.now()}: {text}\n")
        prepared = self.prepare_planned_speech(text)
        self.play_prepared_speech(prepared, filler=filler)  

    ### 文章を文ごとに行動と声色を設定する関数 
    def prepare_planned_speech(self, text):
        plan = ut.build_plan(text)
        voice_map = ut.load_voice_config(CONFIG_PATH_TTS)
        motion_map = ut.load_motion_config(CONFIG_PATH_MOTION)

        prepared = []
        for unit in plan:
            sent = unit["text"]
            label = unit["label"]
            voice = voice_map.get(label)
            motion = motion_map.get(label, {})

            if voice is None:
                continue

            wav_path = tts.synthesize_to_wav(
                sent,
                config_path=CONFIG_PATH_TTS,
                instructions=voice,
                url=tts_url,
            )

            prepared.append({
                "text": sent,
                "label": label,
                "motion": motion,
                "wav_path": wav_path,
                "is_last": unit["is_last"],
            })
            

        return prepared
    
    ### 計画された文章を再生する関数 
    def play_prepared_speech(self, prepared, filler=None):
        def _run():
            self.is_speaking = True
            self.current_prepared = prepared
            self.current_sentence_index = -1
            self.stop_requested = False
            self.stop_after_sentence = False

            try:
                if filler is not None:
                    filler.on_gpt_done_before_tts()
                    filler.scripted_speech_mode = True
                    time.sleep(0.1)

                for idx, item in enumerate(prepared):
                    if self.stop_requested:
                        print("[Chatbot] stop_requested -> break playback loop")
                        break

                    self.current_sentence_index = idx

                    sent = item["text"]
                    motion = item["motion"]

                    print(f"[Chatbot] sent {sent}")

                    self._prepare_playback_motion(filler, motion)
                    near_end_cb = self._build_near_end_callback(
                        filler=filler,
                        motion=motion,
                        is_last=item["is_last"]
                    )

                    done_event = threading.Event()
                    near_end_sec = 2.0 if item["is_last"] else guess_near_end_sec(sent)

                    tts.play_wav(
                        item["wav_path"],
                        done_event=done_event,
                        near_end_sec=near_end_sec,
                        near_end_callback=near_end_cb,
                    )
                    done_event.wait()

                    if self.stop_after_sentence:
                        print("[Chatbot] stop_after_sentence -> break after current sentence")
                        break

            finally:
                self.is_speaking = False
                self.current_prepared = []
                self.current_sentence_index = -1
                self.stop_requested = False
                self.stop_after_sentence = False

                if filler is not None:
                    filler.scripted_speech_mode = False
                    filler.on_tts_done_after_playback()

        threading.Thread(target=_run, daemon=True).start()

    ### 固定された発言（こんにちは、ありがとうなど）に対する関数
    def play_fixed_response(self, fixed_item, filler=None):
        wav_path = Path(fixed_item["wav_path"])
        label = fixed_item.get("label")

        print(f"[Chatbot] Play fixed wav at {datetime.now()}: {wav_path}")

        try:
            motion_map = ut.load_motion_config(CONFIG_PATH_MOTION)
            motion = motion_map.get(label, {}) if label else {}
        except Exception as e:
            logging.warning(f"fixed motion config error: {e}")
            motion = {}

        try:
            self._begin_scripted_speech(filler)
            self._prepare_playback_motion(filler, motion)

            done_event = threading.Event()
            near_end_cb = self._build_near_end_callback(
                filler=filler,
                motion=motion,
                is_last=True
            )

            tts.play_wav(
                wav_path,
                autoremove=False,
                done_event=done_event,
                near_end_sec=1.0,
                near_end_callback=near_end_cb,
            )

            self._start_wait_done_thread(
                done_event,
                filler,
                "[Chatbot] fixed wav playback done"
            )

        except Exception as e:
            self.is_speaking = False
            if filler is not None:
                filler.scripted_speech_mode = False
            logging.warning(f"fixed wav playback error: {e}")
    
    #motion用ヘルパー
    def _prepare_playback_motion(self, filler, motion):
        if filler is None:
            return

        filler.gaze_engage()
        time.sleep(0.1)

        face = motion.get("face")
        if face:
            filler.set_speak_face(face["type"], face["level"])

        bow = motion.get("bow", {})
        if bow.get("enabled"):
            time.sleep(0.2)
            filler.do_bow(bow.get("kind", "small"))

    def _build_near_end_callback(self, filler, motion, is_last):
        if filler is None:
            return None

        fired = threading.Event()

        if not is_last:
            between = motion.get("between_gaze")
            if between:
                def _near_end_callback():
                    if fired.is_set():
                        return
                    fired.set()
                    filler.do_between_sentence_gaze(
                        between.get("type", "l"),
                        between.get("level", 0.3)
                    )
                return _near_end_callback

        def _near_end_callback_last():
            if fired.is_set():
                return
            fired.set()
            filler.gaze_engage()

        return _near_end_callback_last
    
    def _start_wait_done_thread(self, done_event, filler, log_message):
        def _wait_done():
            done_event.wait()
            self.is_speaking = False
            if filler is not None:
                filler.scripted_speech_mode = False
                filler.on_tts_done_after_playback()
            print(log_message)

        threading.Thread(target=_wait_done, daemon=True).start()

    def _begin_scripted_speech(self, filler):
        self.is_speaking = True
        if filler is not None:
            filler.on_gpt_done_before_tts()
            filler.scripted_speech_mode = True
            time.sleep(0.1)

    ### 一言目を生成する関数
    def prefetch_opening_reply(self, mode: str):
        try:
            messages = self.build_base_messages()
            cfg = fixed_reply.get_scenario_config(SCENARIO)
            role = cfg["role"]
            first_task = cfg["first_task"]

            if mode == "greeting":
                user_text = "こんにちは"
                system_text = (
                    "お客様の最初の発話は挨拶です。"
                    f"あなたは{role}です。"
                    "自然な最初の応答を生成してください。"
                    "最初の1文は必ず type='OPENING' の挨拶文にしてください。"
                    f"挨拶から始め、その後に{first_task}"
                )
            elif mode == "call":
                user_text = "すみません"
                system_text = (
                    "お客様の最初の発話は呼びかけです。"
                    f"あなたは{role}です。"
                    "自然な最初の応答を生成してください。"
                    "最初の1文は呼びかけへの応答とし、type='ACCEPT' または type='OPENING' のどちらか自然な方を使ってください。"
                    f"まず呼びかけに応じ、その後に{first_task}"
                )
            else:
                return

            messages.append({
                "role": "system",
                "content": (
                    system_text
                    + " 応答は必ずJSON配列で出力してください。"
                    + " 複数文になる場合は、1文ごとに分割し、それぞれを1要素として配列に入れてください。"
                    + ' 各要素は {"utterance": string, "type": string} の形式にしてください。'
                    + " type は OPENING, STATEMENT, OPINION, QUESTION, APOLOGY, THANKING, CLOSING, ACCEPT のいずれかのみ使ってください。"
                    + " 1つの要素に複数の文を含めてはいけません。"
                    + " 1つの文に対して1つのtypeのみ付与してください。"
                    + " 説明文、補足、Markdown、コードブロックは禁止です。"
                    + " 必ずJSON配列のみを出力してください。"
                )
            })
            messages.append({"role": "user", "content": f"「{user_text}」"})

            resp = openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0,
                max_tokens=128,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )

            reply_text = resp.choices[0].message.content.strip()
            prepared = self.prepare_planned_speech(reply_text)

            self.opening_prefetch[mode] = {
                "reply_text": reply_text,
                "prepared": prepared,
            }

            print(f"[Chatbot] prefetched opening ({mode}): {reply_text}")

        except Exception as e:
            logging.warning(f"prefetch opening error ({mode}): {e}")

    ### 返答をgptを用いて生成する関数
    def generate_reply(self, new_message, filler=None, save_user_text=None):
        with self.lock:
            messages = self.build_base_messages()
            messages = self.append_recent_history(messages)
            messages.append(new_message)
            print(f"[Chatbot] new_messages {new_message}" )

            gpt_response = openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0,
                max_tokens=256,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )

            reply_text = gpt_response.choices[0].message.content.strip()

            self.speak_text_planned(reply_text, filler=filler)
            self.prefetch_short_affirm_reply(reply_text)

            if save_user_text is not None:
                self.addFile.add(save_user_text, reply_text)
                self.history.append({
                    "user": save_user_text,
                    "assistant": reply_text
                })
            else:
                self.history.append({
                    "user": None,
                    "assistant": reply_text
                })

            if len(self.history) > 20:
                self.history = self.history[-20:]

            return reply_text
    
    ### 一つ先の返答を生成する関数
    def prefetch_short_affirm_reply(self, assistant_text):
        def _worker():
            try:
                self.clear_prefetch_reply("replace with newer prefetch")

                messages = self.build_base_messages()
                messages = self.append_recent_history(messages)

                messages.append({
                    "role": "assistant",
                    "content": assistant_text
                })
                messages.append({
                    "role": "system",
                    "content": (
                        "直前のロボット発話に対して、客が『はい』『うん』『お願いします』"
                        "のような短い承諾だけを返した場合の、次のロボット発話を生成してください。"

                        "応答は必ずJSON配列で出力してください。"
                        "複数文になる場合は、1文ごとに分割し、それぞれを1要素として配列に入れてください。"

                        '各要素は {"utterance": string, "type": string} の形式にしてください。'

                        "type は以下のいずれか1つのみ使用してください："
                        "OPENING, STATEMENT, OPINION, QUESTION, APOLOGY, THANKING, CLOSING, ACCEPT。"

                        "1つの要素に複数の文を含めてはいけません。"
                        "1つの文に対して1つのtypeのみ付与してください。"

                        "例："
                        '['
                        '{"utterance": "いらっしゃいませ。", "type": "OPENINIG"},'
                        '{"utterance": "今日はどのようなご用件でしょうか？", "type": "QUESTION"}'
                        ']'

                        "説明文、補足、Markdown、コードブロックは禁止です。"
                        "必ずJSON配列のみを出力してください。"
                    )
                })
                messages.append({"role": "user", "content": "「はい」"})

                resp = openai.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    temperature=0,
                    max_tokens=128,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0
                )

                reply_text = resp.choices[0].message.content.strip()
                prepared = self.prepare_planned_speech(reply_text)

                self.prefetch_reply = {
                    "intent": "short_affirm",
                    "reply_text": reply_text,
                    "prepared": prepared,
                    "source_assistant": assistant_text
                }
                print(f"[Chatbot] 「{reply_text}」を準備しました。")

            except Exception as e:
                logging.warning(f"prefetch error: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    ### 返答を処理
    def handle_user_utterance(self, utterance, filler=None):
        prefetched = self.try_handle_prefetched_reply(utterance, filler=filler)
        if prefetched is not None:
            print(f"[Chatbot] prefetched reply matched: {utterance}")
            filler.on_fixed()
            return prefetched
        
        self.clear_prefetch_reply("prefetch not used")

        prev_type = self.get_last_assistant_da_type()
        fixed_item = fixed_reply.find_fixed_response(utterance, SCENARIO, prev_type) 
        if fixed_item is not None:
            print(f"[Chatbot] fixed response matched: {utterance}")
            filler.on_fixed()
            return self.handle_fixed_response_thanks(utterance, fixed_item, filler=filler)

        return self.generate_reply(
            new_message={"role": "user", "content": f"「{utterance}」"},
            filler=filler,
            save_user_text=utterance
        )                   
    
    ### 固定された返答(挨拶)の処理
    def handle_fixed_response_greeting(self, utterance, opening_key, filler=None):
        cached = self.opening_prefetch.get(opening_key)

        if cached is not None:
            print(f"[Chatbot] opening matched (interim): {utterance} -> {opening_key}")
            filler.on_fixed()

            self.play_prepared_speech(cached["prepared"], filler=filler)
            self.prefetch_short_affirm_reply(cached["reply_text"])

            self.addFile.add(utterance, cached["reply_text"])
            self.history.append({
                "user": utterance,
                "assistant": cached["reply_text"]
            })

            self.skip_next_final_text = fixed_reply.normalize_utterance(utterance)

    ### 固定された返答(感謝)の処理
    def handle_fixed_response_thanks(self, utterance, fixed_item, filler=None):
        reply_text = fixed_item["reply_text"]

        self.play_fixed_response(fixed_item, filler=filler)
        self.prefetch_short_affirm_reply(reply_text)

        self.addFile.add(utterance, reply_text)
        self.history.append({
            "user": utterance,
            "assistant": reply_text
        })

        if len(self.history) > 20:
            self.history = self.history[-20:]

        return reply_text
    
    def get_last_assistant_da_type(self) -> str | None:
        if not self.history:
            return None

        last = self.history[-1].get("assistant")
        if not last:
            return None

        try:
            items = parse_reply_json(last)
            return items[-1]["type"]  # ← 最後の文
        except Exception:
            return None
    
    ### 固定された返答(承諾)への処理
    def try_handle_prefetched_reply(self, utterance, filler=None):
        if self.prefetch_reply is None:
            return None

        if not fixed_reply.is_short_affirm(utterance):
            return None

        cached = self.prefetch_reply
        self.prefetch_reply = None

        self.play_prepared_speech(cached["prepared"], filler=filler)
        self.prefetch_short_affirm_reply(cached["reply_text"])

        self.addFile.add(utterance, cached["reply_text"])
        self.history.append({
            "user": utterance,
            "assistant": cached["reply_text"]
        })
        if len(self.history) > 20:
            self.history = self.history[-20:]

        return cached["reply_text"]

    ### Enter入力に対する処理
    def handle_internal_event_next(self, filler=None):
        if self.prefetch_reply is not None:
            print("[Chatbot] use prefetched reply for next")

            cached = self.prefetch_reply
            self.prefetch_reply = None

            self.play_prepared_speech(cached["prepared"], filler=filler)
            self.prefetch_short_affirm_reply(cached["reply_text"])

            self.history.append({
                "user": None,
                "assistant": cached["reply_text"]
            })

            return cached["reply_text"]

        # fallback（万が一）
        return self.generate_reply(
            new_message={"role": "system", "content": "次に進めてください"},
            filler=filler,
            save_user_text=None
        )
    
    ### 割り込みに対する処理
    def get_current_robot_sentence_text(self) -> str:
        if not self.current_prepared:
            return ""
        if self.current_sentence_index < 0:
            return ""
        if self.current_sentence_index >= len(self.current_prepared):
            return ""
        return self.current_prepared[self.current_sentence_index].get("text", "")
    
    def get_current_robot_sentence_type(self) -> str:
        if not self.current_prepared:
            return ""
        if self.current_sentence_index < 0:
            return ""
        if self.current_sentence_index >= len(self.current_prepared):
            return ""
        return self.current_prepared[self.current_sentence_index].get("type", "")

    def current_sentence_is_last(self) -> bool:
        if not self.current_prepared:
            return False
        if self.current_sentence_index < 0:
            return False
        if self.current_sentence_index >= len(self.current_prepared):
            return False
        return bool(self.current_prepared[self.current_sentence_index].get("is_last", False))

    def request_stop_now(self, filler=None):
        print("[Chatbot] request_stop_now")
        self.stop_requested = True

        try:
            tts._player.stop_current()
        except Exception as e:
            logging.warning(f"interrupt stop error: {e}")

        self.is_speaking = False
        if filler is not None:
            filler.on_tts_done_after_playback()

    def request_stop_after_sentence(self):
        print("[Chatbot] request_stop_after_sentence")
        self.stop_after_sentence = True

    def handle_interrupt_interim(self, utterance, filler=None):
        decision = self.interrupt_handler.decide(
            text=utterance,
            current_robot_text=self.get_current_robot_sentence_text(),
            current_robot_type=self.get_current_robot_sentence_type(),
            is_last_sentence=self.current_sentence_is_last(),
        )

        print(
            f"[Chatbot] interrupt interim decision: "
            f"da={decision.da}, policy={decision.policy}, source={decision.source}"
        )

        if decision.policy == "continue":
            # 軽い反応だけして継続
            if filler is not None:
                filler.on_fixed()
            return "continue"

        if decision.policy == "stop_now":
            self.request_stop_now(filler=filler)
            return "stop_now"

        if decision.policy == "stop_after_sentence":
            self.request_stop_after_sentence()
            return "stop_after_sentence"

        return None

    def handle_interrupt_final(self, utterance, filler=None):
        decision = self.interrupt_handler.decide(
            text=utterance,
            current_robot_text=self.get_current_robot_sentence_text(),
            current_robot_type=self.get_current_robot_sentence_type(),
            is_last_sentence=self.current_sentence_is_last(),
        )

        print(
            f"[Chatbot] interrupt final decision: "
            f"da={decision.da}, policy={decision.policy}, source={decision.source}"
        )

        if decision.policy == "continue":
            # 相槌・感謝はそのまま流す
            if filler is not None:
                filler.on_fixed()
            return None

        if decision.policy == "stop_now":
            self.request_stop_now(filler=filler)

            # 割り込み内容を優先して新規応答
            return self.generate_reply(
                new_message={
                    "role": "system",
                    "content": (
                        "ロボットの発話中にお客様が割り込みました。"
                        f"割り込み内容は「{utterance}」です。"
                        "直前の案内を中断し、お客様の発話を優先して自然に応答してください。"
                        "必要なら最初に短く謝罪してください。"
                    )
                },
                filler=filler,
                save_user_text=utterance
            )

        if decision.policy == "stop_after_sentence":
            self.request_stop_after_sentence()

            # 最小差分版なので、いったん現在文の後で即応答生成
            # ここは本来キュー化した方がきれいだが、まずは簡易に少し待つ
            def _delayed_reply():
                time.sleep(0.2)
                self.generate_reply(
                    new_message={
                        "role": "system",
                        "content": (
                            "ロボットの発話中にお客様が割り込みました。"
                            f"割り込み内容は「{utterance}」です。"
                            "ロボットは現在の文だけ話し終えてから、お客様の発話に自然に応答してください。"
                        )
                    },
                    filler=filler,
                    save_user_text=utterance
                )

            threading.Thread(target=_delayed_reply, daemon=True).start()
            return None

        return None
    ### 未使用wavを消す
    def _cleanup_prepared_wavs(self, prepared):
        if not prepared:
            return

        for item in prepared:
            try:
                wav_path = item.get("wav_path")
                if wav_path is None:
                    continue
                Path(wav_path).unlink(missing_ok=True)
                print(f"[Chatbot] removed unused wav: {wav_path}")
            except Exception as e:
                logging.warning(f"unused wav cleanup error: {e}")

    def clear_prefetch_reply(self, reason=""):
        if self.prefetch_reply is None:
            return

        cached = self.prefetch_reply
        self.prefetch_reply = None

        self._cleanup_prepared_wavs(cached.get("prepared"))

        if reason:
            print(f"[Chatbot] discard prefetched reply: {reason}")
        else:
            print("[Chatbot] discard prefetched reply")

#### ---- メインで動かす関数　---- ####
    def run(self):
        try:
            system_content, system_content2 = self.load_prompt_config()
            # print(f"[Chatbot] system_content1: {system_content}")

            xyz = XYZClient()
            xyz.start()

            robot = RobotCommandClient(host="nikola-humantracker", port=8078, eol="lf")
            robot.connect()
            filler = FillerController(xyz, robot)
            start_tick_thread(filler)

            self.prefetch_opening_reply("greeting")
            self.prefetch_opening_reply("call")

            # Enterだけで「次へ進む」を呼ぶ
            def next_button_listener():
                while True:
                    try:
                        cmd = input().strip()
                        print("[Chatbot] internal event: next")
                        self.handle_internal_event_next(filler=filler)
                    except EOFError:
                        break
                    except Exception as e:
                        print(f"[Chatbot] input thread error: {e}")

            threading.Thread(target=next_button_listener, daemon=True).start()

            for ev in iter_asr_events(HOST, PORT):
                utterance = ev.text
                confidence = ev.conf
                ts = ev.ts

                speaking_now = self.is_speaking or filler.tts_playing

                if ev.kind == "interim":
                    filler.on_interim(utterance)
                    if speaking_now:
                        result = self.handle_interrupt_interim(utterance, filler=filler)
                        print(f"[Chatbot] ASR interrupt interim at {ts}: {utterance} -> {result}")
                        continue

                    if not self.history:
                        opening_key = fixed_reply.find_opening_prefetch_key(utterance, SCENARIO)
                        if opening_key is not None:
                            self.handle_fixed_response_greeting(utterance,opening_key=opening_key, filler=filler)
                        continue

                    prefetched = fixed_reply.is_short_affirm(utterance)
                    if prefetched:
                        print(f"[Chatbot] is_short_affirm matched (interium): {utterance}")
                        filler.on_fixed()

                    prev_type = self.get_last_assistant_da_type()
                    fixed_item = fixed_reply.find_fixed_response(utterance, SCENARIO, prev_type)
                    if fixed_item is not None:
                        print(f"[Chatbot] fixed response matched (interium): {utterance}")
                        filler.on_fixed()
                    print(f"[Chatbot] ASR interim at {ts}: {utterance}")
                    continue

                
                if confidence is not None:
                    print(f"[Chatbot] ASR result ({confidence:.2f}) at {ts}: {utterance}")
                else:
                    print(f"[Chatbot] ASR result at {ts}: {utterance}")

                norm_final = fixed_reply.normalize_utterance(utterance)
                if self.skip_next_final_text is not None and norm_final == self.skip_next_final_text:
                    print(f"[Chatbot] skip final because already handled by interim: {utterance}")
                    self.skip_next_final_text = None
                    continue

                if speaking_now:
                    self.handle_interrupt_final(utterance, filler=filler)
                    continue

                filler.on_final()
                self.handle_user_utterance(utterance, filler=filler)

        except KeyboardInterrupt:
            filler.on_interrupt()
            self.clear_prefetch_reply("prefetch not used")
            print("\n[Chatbot] Ctrl+C を検知しました。サーバーを終了します。")
            try:
                tts._player.stop()
            except Exception:
                pass
            sys.exit(0)


if __name__ == "__main__":
    print("[Chatbot] 起動")
    style_change_server = StyleChangeServer()
    style_change_server.run()