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

from filler.asr_stream import iter_asr_events
from filler.robot_client import RobotCommandClient
from filler.filler_controller import FillerController
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
STSTEM_CONTENT = system_content_file.system_content_hotel_checkin


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


class StyleChangeServer(object):
    def __init__(self, port=13204):
        self.addFile = StringFile(1)
        self.history = []   # [{"user": ..., "assistant": ...}, ...]
        self.is_speaking = False
        self.lock = threading.Lock()
        self.last_style_mtime = None
        self.cached_style_prompt = ""

    def load_prompt_config(self):
        system_content = STSTEM_CONTENT
        system_content2 = self.refresh_style_prompt_if_needed()
        return system_content, system_content2

    def build_base_messages(self):
        system_content, system_content2 = self.load_prompt_config()

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
        # 直近 MAX_TURNS 往復を追加
        recent = self.history[-MAX_TURNS:]
        for turn in recent:
            if turn.get("user"):
                messages.append({"role": "user", "content": f"「{turn['user']}」"})
            if turn.get("assistant"):
                messages.append({"role": "assistant", "content": f"「{turn['assistant']}」"})
        return messages

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

    def speak_text_planned(self, text, filler=None):
        print(f"[Chatbot] Send at {datetime.now()}: {text}\n")

        try:
            plan = ut.build_plan(text)
            voice_map = ut.load_voice_config(CONFIG_PATH_TTS)
            motion_map = ut.load_motion_config(CONFIG_PATH_MOTION)
        except Exception as e:
            logging.warning(f"plan/config error: {e}")
            return self.speak_text(text, filler=filler)

        def _run():
            self.is_speaking = True
            try:
                if filler is not None:
                    filler.on_gpt_done_before_tts()
                    filler.scripted_speech_mode = True
                    time.sleep(1.0)

                # まず全wavを作る
                prepared = []
                for unit in plan:
                    sent = unit["text"]
                    label = unit["label"]
                    voice = voice_map.get(label)
                    motion = motion_map.get(label, {})

                    if voice is None:
                        logging.warning(f"voice label not found: {label}")
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
                print(f"[Chatbot] prepared:{prepared}")

                # できたwavを順番に再生
                for item in prepared:
                    sent = item["text"]
                    motion = item["motion"]

                    print(f"[Chatbot] play: {sent}")

                    if filler is not None:
                        filler.gaze_engage()
                        time.sleep(0.1)

                    face = motion.get("face")
                    if filler is not None and face:
                        filler.set_speak_face(face["type"], face["level"])

                    bow = motion.get("bow", {})
                    if filler is not None and bow.get("enabled"):
                        time.sleep(0.2)
                        filler.do_bow(bow.get("kind", "small"))

                    near_end_cb = None

                    if filler is not None:
                        fired = threading.Event()

                        if not item["is_last"]:
                            between = motion.get("between_gaze")
                            if between:
                                def _near_end_callback(between=between, fired=fired):
                                    if fired.is_set():
                                        return
                                    fired.set()
                                    filler.do_between_sentence_gaze(
                                        between.get("type", "l"),
                                        between.get("level", 0.3)
                                    )
                                near_end_cb = _near_end_callback

                        else:
                            def _near_end_callback_last(fired=fired):
                                if fired.is_set():
                                    return
                                fired.set()
                                filler.gaze_engage()
                            near_end_cb = _near_end_callback_last

                    done_event = threading.Event()

                    if item["is_last"]:
                        near_end_sec = 2.0
                    else:
                        near_end_sec = guess_near_end_sec(sent)

                    tts.play_wav(
                        item["wav_path"],
                        done_event=done_event,
                        near_end_sec=near_end_sec,
                        near_end_callback=near_end_cb,
                    )
                    done_event.wait()

            except Exception as e:
                logging.warning(f"planned TTS error: {e}")
            finally:
                self.is_speaking = False
                if filler is not None:
                    filler.scripted_speech_mode = False
                    filler.on_tts_done_after_playback()
                print("[Chatbot] planned TTS playback done")

        threading.Thread(target=_run, daemon=True).start()

    
    
    def generate_reply(self, new_message, filler=None, save_user_text=None):
        """
        new_message:
            例1: {"role": "user", "content": "「こんにちは」"}
            例2: {"role": "system", "content": "内部イベント: 次へ進む ..."}
        save_user_text:
            実際に履歴に user として残したい文字列。
            内部イベントのときは None でよい。
        """
        with self.lock:
            messages = self.build_base_messages()
            messages = self.append_recent_history(messages)
            messages.append(new_message)

            gpt_response = openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0,
                max_tokens=128,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )

            pol_msg = gpt_response.choices[0].message.content
            gpt_response_text = remove_quotes(pol_msg)

            self.speak_text_planned(gpt_response_text, filler=filler)

            # 履歴保存
            if save_user_text is not None:
                self.addFile.add(save_user_text, gpt_response_text)
                self.history.append({
                    "user": save_user_text,
                    "assistant": gpt_response_text
                })
            else:
                # 内部イベントは user 発話としては残さず、
                # assistant だけ追加したいならこういう保存でもよい
                self.history.append({
                    "user": None,
                    "assistant": gpt_response_text
                })

            # 履歴を増やしすぎない
            if len(self.history) > 20:
                self.history = self.history[-20:]

            return gpt_response_text

    def handle_user_utterance(self, utterance, filler=None):
        return self.generate_reply(
            new_message={"role": "user", "content": f"「{utterance}」"},
            filler=filler,
            save_user_text=utterance
        )

    def handle_internal_event_next(self, filler=None):
        internal_prompt = (
            "内部イベント: 次へ進む。"
            "ロボットは自分の発話権を保持しています。"
            "直前までの会話文脈を踏まえて、次に客へ伝える自然な一言を1文で生成してください。"
            "ただし、会話中に出ていない新しい事実を付け加えてはいけません。"
            "直前の会話が確認を待つように指示した場合、確認を終わらせ、在庫や空きがあったとして会話を進めてください"
            "客の返答を必須としない、自然な案内・説明・つなぎの発話にしてください。"
            "直前の会話がない場合は、挨拶を行ってください"
        )

        return self.generate_reply(
            new_message={"role": "system", "content": internal_prompt},
            filler=filler,
            save_user_text=None
        )

    def run(self):
        try:
            system_content, system_content2 = self.load_prompt_config()
            print(f"[Chatbot] system_content1: {system_content}")

            xyz = XYZClient()
            xyz.start()

            robot = RobotCommandClient(host="nikola-humantracker", port=8078, eol="lf")
            robot.connect()
            filler = FillerController(xyz, robot)
            start_tick_thread(filler)

            # 例: デバッグ用に別スレッドで Enter 入力を受ける
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

                if ev.kind == "interim":
                    filler.on_interim(ev.text)
                    print(f"[Chatbot] ASR interim at {ts}: {utterance}")
                    continue

                filler.on_final()
                if confidence is not None:
                    print(f"[Chatbot] ASR result ({confidence:.2f}) at {ts}: {utterance}")
                else:
                    print(f"[Chatbot] ASR result at {ts}: {utterance}")

                self.handle_user_utterance(utterance, filler=filler)

        except KeyboardInterrupt:
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