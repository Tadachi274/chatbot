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
import tts_openai 
import tts_voicevox2 as tts_voicevox
import system_content_file 

import json
from pathlib import Path

openai.api_key = os.getenv("OPENAI_API_KEY")
SYSTEM_CONTENT = system_content_file.system_content_america_closingtime


#def run(config_path="voice_config_openai.json",tts_server="openai"):
def run(config_path="voice_config1.json",tts_server="voicevox"):
    try:
        # Word Conversion
        system_content = SYSTEM_CONTENT
        
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

        system_content2 = config['gpt_system']
        print(f"system_content2: {system_content2}")

        utterance = input("Enter your message: ")
        print(f"input:{datetime.now()}")

        messages=[
        {"role": "system", "content": system_content},{"role": "system", "content": system_content2}]

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
        response = response.choices[0].message.content

        # Show results:
        print(f"output:{datetime.now()}")
        print(f"Send: {response}")
    
        # 非同期でOpenAI TTSを呼び出し、再生し、保存する
        try:
            # 保存先パスの生成
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_dir = Path("audio_outputs")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"{timestamp}.wav"

            # 音声の再生と保存
            if(tts_server=="openai"):
                tts_openai.save_audio(response, str(output_path), config_path)
            elif(tts_server=="voicevox"):
                #tts_voicevox.speak_async(response,config_path)
                tts_voicevox.save_audio(response, str(output_path), config_path)

        except Exception as e:
            logging.warning(f"TTS error: {e}")

    except KeyboardInterrupt:
        print("\nCtrl+C を検知しました。サーバーを終了します。")
            
if __name__ == "__main__":
    print("Starting chatbot test...")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run()