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
SCENARIO = "hotel"
STSTEM_CONTENT = system_content_file.souvenir


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
        self.prefetch_reply = None

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
            try:
                if filler is not None:
                    filler.on_gpt_done_before_tts()
                    filler.scripted_speech_mode = True
                    time.sleep(0.1)

                for item in prepared:
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
            finally:
                self.is_speaking = False
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

    ### 返答をgptを用いて生成する関数
    def generate_reply(self, new_message, filler=None, save_user_text=None):
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
            self.prefetch_short_affirm_reply(gpt_response_text)

            if save_user_text is not None:
                self.addFile.add(save_user_text, gpt_response_text)
                self.history.append({
                    "user": save_user_text,
                    "assistant": gpt_response_text
                })
            else:
                self.history.append({
                    "user": None,
                    "assistant": gpt_response_text
                })

            if len(self.history) > 20:
                self.history = self.history[-20:]

            return gpt_response_text
    
    ### 一つ先の返答を生成する関数
    def prefetch_short_affirm_reply(self, assistant_text):
        def _worker():
            try:
                self.clear_prefetch_reply("replace with newer prefetch")

                messages = self.build_base_messages()
                messages = self.append_recent_history(messages)

                messages.append({"role": "assistant", "content": f"「{assistant_text}」"})
                messages.append({
                    "role": "system",
                    "content": (
                        "直前のロボット発話に対して、客が『はい』『うん』『お願いします』"
                        "のような短い承諾だけを返した場合の、次のロボット発話を2文生成してください。"
                        "会話を自然に一歩進めてください。"
                        "確認待ちだった場合は、承諾されたものとして次の案内に進んでください。"
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

                reply_text = remove_quotes(resp.choices[0].message.content)
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

        fixed_item = fixed_reply.find_fixed_response(utterance, SCENARIO)
        if fixed_item is not None:
            print(f"[Chatbot] fixed response matched: {utterance}")
            filler.on_fixed()
            return self.handle_fixed_response(utterance, fixed_item, filler=filler)

        return self.generate_reply(
            new_message={"role": "user", "content": f"「{utterance}」"},
            filler=filler,
            save_user_text=utterance
        )                   
    
    ### 固定された返答(挨拶)の処理
    def handle_fixed_response(self, utterance, fixed_item, filler=None):
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
                    filler.on_interim(utterance)
                    prefetched = fixed_reply.is_short_affirm(utterance)
                    if prefetched:
                        print(f"[Chatbot] is_short_affirm matched (interium): {utterance}")
                        filler.on_fixed()
                    fixed_item = fixed_reply.find_fixed_response(utterance, SCENARIO)
                    if fixed_item is not None:
                        print(f"[Chatbot] fixed response matched (interium): {utterance}")
                        filler.on_fixed()
                    print(f"[Chatbot] ASR interim at {ts}: {utterance}")
                    continue

                filler.on_final()
                if confidence is not None:
                    print(f"[Chatbot] ASR result ({confidence:.2f}) at {ts}: {utterance}")
                else:
                    print(f"[Chatbot] ASR result at {ts}: {utterance}")

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