#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
from datetime import datetime
import logging
import numpy as np
import zmq
from string_to_file import StringFile
import openai
import os
import tts_openai as tts
import json
from pathlib import Path
import system_content_file 

openai.api_key = os.getenv("OPENAI_API_KEY")

def remove_quotes(text):
    if text.startswith('「') and text.endswith('」'):
        return text[1:-1]
    return text


class StyleChangeServer(object):
    def __init__(self, port=13204):
        self.addFile = StringFile(1)
        self.history = []
        
    def run(self,config_path="voice_config_openai.json"):
        try:
            while True:
                # Word Conversion
                system_content = system_content_file.system_content_america
                
                config_file = Path(config_path)
                if config_file.exists():
                    with open(config_file, "r", encoding="utf-8") as f:
                        config = json.load(f)

                system_content2 = config['gpt_system']

                utterance = input("Enter your message: ")
                print(f"input:{datetime.now()}")
                
                user_content = utterance
                #user_content = "こんにちは"
    
                messages=[
                {"role": "system", "content": system_content},{"role": "system", "content": system_content2}]
    
                # 過去のやり取りを user/assistant ペアで追加
                for past_u, past_r in self.history:
                    messages.append({"role": "user",      "content": f"「{past_u}」"})
                    messages.append({"role": "assistant", "content": f"「{past_r}」"})
    
                # 今回のユーザ発話
                messages.append({"role": "user", "content": f"「{utterance}」"})
    
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0,
                    max_tokens=256,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0
                )
                pol_msg = response.choices[0].message.content
                response = remove_quotes(pol_msg)
    
                
                # Show results:
                print(f"output:{datetime.now()}")
                print(f"Send: {response}")
                print()
                # 非同期でOpenAI TTSを呼び出し、再生
                #try:
                #    tts.speak_async(response)
                #except Exception as e:
                #    logging.warning(f"TTS error: {e}")
                # Logging to file

                try:
                    # 保存先パスの生成
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    output_dir = Path("audio_outputs")
                    output_dir.mkdir(exist_ok=True)
                    output_path = output_dir / f"{timestamp}.wav"

                    # 音声の再生と保存
                    tts.save_audio(response, str(output_path), config_path="voice_config_openai.json")
                    
                except Exception as e:
                    logging.warning(f"TTS error: {e}")
    
                log_str = f" {datetime.now().timestamp():f} "
                self.addFile.add(utterance, response)
                # メモリにも追加
                self.history.append((utterance, response))
        except KeyboardInterrupt:
            print("\nCtrl+C を検知しました。サーバーを終了します。")
            
if __name__ == "__main__":

    print("起動")

    parser = argparse.ArgumentParser(description='Run a server for filtering words')
    parser.add_argument('--port', type=int, default=13204, help='port on which the server listen')

    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    style_change_server = StyleChangeServer()
    style_change_server.run()