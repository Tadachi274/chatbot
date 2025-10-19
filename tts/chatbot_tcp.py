#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
import logging
from string_to_file import StringFile
import openai
import os
from dotenv import load_dotenv
import tts_openai as tts
import json
from pathlib import Path
import system_content_file 
import sys
import socket  

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT", 8888))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")    

def remove_quotes(text):
    if text.startswith('「') and text.endswith('」'):
        return text[1:-1]
    return text

class StyleChangeServer(object):
    def __init__(self, port=13204):
        self.addFile = StringFile(1)
        self.history = []
        
    def receive_asr_results(self, host=HOST, port=PORT):
        """
        Connect to ASR TCP server and yield (final_text, confidence) whenever a 'result:' arrives.
        Expected lines:
          Interimresult: <text>
          result: <text>
          confidence: <float>
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        buf = ""
        last_conf = None
        try:
            print(f"Connected to ASR stream at {host}:{port}")
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    print("ASR connection closed.")
                    return
                buf += chunk.decode("utf-8", errors="ignore")
                # normalize newlines
                buf = buf.replace("\r\n", "\n").replace("\r", "\n")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    low = line.lower()
                    if low.startswith("interimresult:"):
                        interim = line.split(":", 1)[1].strip()
                        if interim:
                            print(f"[ASR interim] {interim}")
                    elif low.startswith("confidence:"):
                        val = line.split(":", 1)[1].strip()
                        try:
                            last_conf = float(val)
                        except Exception:
                            last_conf = None
                    elif low.startswith("result:"):
                        final_text = line.split(":", 1)[1].strip()
                        if final_text:
                            yield final_text, last_conf
        finally:
            try:
                sock.close()
            except Exception:
                pass

    def run(self,config_path="voice_config_openai.json"):
        try:
            system_content = system_content_file.system_content_raw
            ### American Version
            # system_content = system_content_file.system_content_america
            print(f"system_content: {system_content}")
            config_file = Path(config_path)

            # Listen to ASR stream and handle each final result
            for utterance, confidence in self.receive_asr_results(HOST, PORT):
                if config_file.exists():
                    with open(config_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                else:
                    print(f"Config file not found: {config_path}")
                    return 

                system_content2 = config['gpt_system']
                print(f"system_content2: {system_content2}")

                ts = datetime.now()
                if confidence is not None:
                    print(f"ASR result ({confidence:.2f}) at {ts}: {utterance}")
                else:
                    print(f"ASR result at {ts}: {utterance}")
    
                messages=[
                {"role": "system", "content": system_content},
                {"role": "system", "content": f"話し方の要望は以下の通りです。{system_content2}"}]
    
                # 過去のやり取りを user/assistant ペアで追加
                for past_u, past_r in self.history:
                    messages.append({"role": "user",      "content": f"「{past_u}」"})
                    messages.append({"role": "assistant", "content": f"「{past_r}」"})
    
                # 今回のユーザ発話
                messages.append({"role": "user", "content": f"「{utterance}」"})
    
                response = openai.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    temperature=0,
                    max_tokens=256,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0
                )
                pol_msg = response.choices[0].message.content
                response_text = remove_quotes(pol_msg)
    
                # Show results:
                print(f"output:{datetime.now()}")
                print(f"Send: {response_text}\n")
                try:
                    tts.speak_async(response_text,config_path=config_path)
                except Exception as e:
                    logging.warning(f"TTS error: {e}")
                self.addFile.add(utterance, response_text)
                self.history.append((utterance, response_text))
        except KeyboardInterrupt:
            print("\nCtrl+C を検知しました。サーバーを終了します。")
            try:
                tts._player.stop()
            except Exception:
                pass
            sys.exit(0)

if __name__ == "__main__":

    print("起動")

    style_change_server = StyleChangeServer()
    style_change_server.run()