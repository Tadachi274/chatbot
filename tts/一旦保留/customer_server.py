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

openai.api_key = os.getenv("OPENAI_API_KEY")

def remove_quotes(text):
    if text.startswith('「') and text.endswith('」'):
        return text[1:-1]
    return text


class StyleChangeServer(object):
    def __init__(self, port=13204):
        server_uri=f"tcp://127.0.0.1:{port}"

        context = zmq.Context()
        self.socket = context.socket(zmq.REP)
        self.socket.bind(server_uri)

        self.addFile = StringFile(1)
        self.history = []

    def run(self):
        self.socket.RCVTIMEO = 1000  # 1000ms = 1秒のタイムアウト

        try:
            while True:
                # Get request
                try:
                    utterance = self.socket.recv_string()
                except zmq.Again:
                    continue  # タイムアウト → 再試行
                print(f"Received {utterance}")
    
                # low confidence
                if (utterance == "(low confidence)"):
                    response = "(音声を読み取れませんでした)"
                    self.socket.send(response.encode('utf-8'))
    
                    # Show results:
                    print(f"Send: {response}")
                    print()
    
                    # Logging to file
                    log_str = f" {datetime.now().timestamp():f} "
                    self.addFile.add(utterance, response)
    
                    continue
    
                # Word Conversion
                system_content = """
    Note that the Japanese sentences I provide are statements made by a customer to the store staff.
    Please serve customers as a clerk in a Kyoto souvenir shop.
    """
                system_content2 = """
                Speak like Goku from Dragon Ball"""
    
                user_content = utterance
                #user_content = "こんにちは"
                print(utterance)
    
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
    
                # Send Resul
                self.socket.send(response.encode('utf-8'))
    
                # 非同期でOpenAI TTSを呼び出し、再生
                try:
                    tts.speak_async(
                        response,
                        model="tts-1",          # 高速重視なら "tts-1"
                        voice="alloy"           # 好みの声に変更可
                    )
                except Exception as e:
                    logging.warning(f"TTS error: {e}")
    
                # Show results:
                print(f"Send: {response}")
                print()
    
                # Logging to file
    
                log_str = f" {datetime.now().timestamp():f} "
                self.addFile.add(utterance, response)
                # メモリにも追加
                self.history.append((utterance, response))
        except KeyboardInterrupt:
            print("\nCtrl+C を検知しました。サーバーを終了します。")
            self.socket.close()

if __name__ == "__main__":

    print("起動")

    parser = argparse.ArgumentParser(description='Run a server for filtering words')
    parser.add_argument('--port', type=int, default=13204, help='port on which the server listen')

    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    style_change_server = StyleChangeServer()
    style_change_server.run()