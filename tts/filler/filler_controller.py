# filler_controller.py
import time
from typing import Optional
import json
import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ..tts_audioplayer import AudioPlayer
import random
import wave

TAIL_WEAK   = ("です", "ます", "でした", "ました", "ですね", "ですよ", "けど", "ので", "から")
TAIL_Q      = ("ですか", "ますか", "でしょうか", "ですかね", "ますかね")
TAIL_CONT   = ("ですけど", "ますけど", "けど", "けども", "ですが", "ですけどね")

DEFAULT_FILLERS = ("んん","はい","ええ","えっと","あの")
DEFAULT_CANTHEAR = ("すみませんもう一度よろしいでしょうか")
FILLER_RATE = 0.3

class FillerController:
    def __init__(self, xyz_client, robot_client):
        now = time.monotonic()
        self.xyz = xyz_client
        self.robot = robot_client

        self.last_interim_t = 0.0
        self.last_interim_text = ""

         # --- nod(listen)用 ---
        self._last_listen_nod_t = 0.0 #最後に頷いた時間
        self._last_meaning_t = 0.0 # 意味が進んだ最後の時刻
        self._best_clean = ""  # 内容として一番進んだ文字列（clean済み）
        self._last_nod_best_len = 0
        self.LISTEN_NOD_COOLDOWN = 1.8 #頷きの最低間隔
        self.LISTEN_NOD_MIN_PAUSE = 0.0 #話まくしたて中に頷かない
        self.LISTEN_NOD_STEP = 8 #意味がどれだけ進んだら頷くか

        self._best_tail_type = "none"

        self.noding = False
        self.noding_first = True
        self.gpt_thinking = False
        self.waiting = False  # WAIT中は視線を戻さない
        self.tts_playing = False
        self.matching = True
        self.fixed = False

        # クールダウン
        self._last_fail_t = 0.0
        self._last_wait_face_t = 0.0
        self._last_listen_face_t = 0.0
        self._last_speak_face_t = 0.0
        self.tts_near_end_engage = False
        self._last_gaze_match_t = 0.0
        self._last_gaze_avert_t = 0.0

        # パラメータ（まずはこれで）
        self.INTERIM_OK_interval = 0.6
        self.INTERIM_FAIL_interval = 3.0
        self.NOD_COOLDOWN = 1.3
        self.FAIL_COOLDOWN = 5.0
        self.FACE_COOLDOWN = 2.0

        self.ASR_GRACE_ON_SPEECH = 2.0  # act>=1になってからinterimが来るまでの猶予秒

        self._prev_act = 0
        self._act_on_t = 0.0

        self._face_cfg_path = Path(__file__).with_name("filler_face_state.json")
        self._face_cfg_mtime = 0.0
        data = json.loads(self._face_cfg_path.read_text(encoding="utf-8"))
        self._faces = data.get("faces", {})
        self.face_keys = [k for k in self._faces.keys()]
        for k in self.face_keys:
            if k in self._faces:
                f = self._faces[k]
                self._faces[k] = {
                    "type": str(f.get("type")),
                    "level": f.get("level"),
                    }
                
        self._filler_cfg_path = Path(__file__).with_name("filler_voice_state.json")
        data = json.loads(self._filler_cfg_path.read_text(encoding="utf-8"))
        self._fillers = data.get("fillers", {})
        self._fillers_rate = data.get("rate", {})

        self._player = AudioPlayer(autoremove=False)

    def _reload_face_cfg_if_needed(self):
        try:
            st = self._face_cfg_path.stat()
        except FileNotFoundError:
            print("Fileが見つかりません")
            return
        except Exception:
            print("Fileが読み取れません")
            return

        if st.st_mtime <= self._face_cfg_mtime:
            return

        try:
            data = json.loads(self._face_cfg_path.read_text(encoding="utf-8"))
            faces = data.get("faces", {})
            for k in self.face_keys:
                if k in faces:
                    f = faces[k]
                    self._faces[k] = {
                        "type": str(f.get("type", self._faces[k]["type"])),
                        "level": f.get("level", self._faces[k]["level"]),
                        }
            self._face_cfg_mtime = st.st_mtime
        except Exception:
            self._face_cfg_mtime = st.st_mtime
            return

    def _get_act(self) -> int:
        s = self.xyz.get_latest()
        return int(getattr(s, "act", 0)) if s else 0

    def _get_xyz(self):
        return self.xyz.get_latest()
    
    def _classify_tail(self, text: str) -> str:
        t = text.strip()
        # 疑問は最優先
        if any(t.endswith(x) for x in TAIL_Q):
            return "q"
        # 継続（ですけど…）は「まだ続く」なので頷きは弱め/遅めにしたい
        if any(t.endswith(x) for x in TAIL_CONT):
            return "cont"
        # 弱い（です/ます単体）
        if any(t.endswith(x) for x in TAIL_WEAK):
            return "weak"
        return "none"
    
    def _clean_interim(self, text: str) -> str:
        t = (text or "").strip()
        # よく出るフィラーを削除（必要に応じて追加）
        for w in ["えっと", "えー", "あの", "その", "なんか", "あー"]:
            t = t.replace(w, "")
        # 空白を詰める
        t = " ".join(t.split())
        return t
    
    def _filler_choice(self, canthear:bool=False, listen:bool=False):
        p = self._faces["speak_person"]
        dir_path = Path(__file__).resolve().parent.parent / "filler" / f"{p['type']}"
        wav_name = random.choice(self._fillers)

        if canthear:
            dir_path = dir_path / "canthear" 
            wav_name = DEFAULT_CANTHEAR
        
        wav_path = next(dir_path.glob(f"{wav_name}.wav"))

        if listen:
            wav_path = next(dir_path.glob("はい*"), None)
            if wav_path is None:
                wav_path = next(dir_path.glob("んん*"), None)

        if self.noding_first and not canthear:
            wav_path = next(dir_path.glob("はい*"))
            self.noding_first = False

        print(f"[FillerController] filler_choice {wav_path}")
        if random.random() <= self._fillers_rate:
            self._player.play_later(wav_path)
        else:
            print(f"[FillerController] filler don't play")

        return wav_path
    
    def create_lookaway(self,payload,level):
        delta = 400 * round(level,2)
        s = self._get_xyz()
        if not s:
            return
        x = s.x
        y = s.y
        z = s.z
        if "u" in payload:
            z += delta*2
        if "d" in payload:
            z -= delta*0.5
        if "l" in payload:
            y -= delta
        if "r" in payload:
            y += delta
        command = f"/look {x} {y} {z} 1.0 0 0 4 1500"
        if "d" in payload:
            command = f"/lookaway {payload} 4 1500 0.5"

        return command
    
    def _create_listen_nod(self):
        n = self._faces["listen_nod"]
        v = self._faces["listen_voice"]
        e = self._faces["listen_emotion"]
    
        if v['level'] == 1:
            self._filler_choice(listen=True)

        priority = 3
        if n["type"] == "small":
            self.robot.send(f"/nod 7 300 {n["level"]} {priority}") 
            time.sleep(0.1)
            self.robot.send(f"/blink {300*0.9}")
        elif n["type"] == "mid":
            if n["level"]==1:
                self.robot.send(f"/nod 10 400 {n["level"]} {priority}") 
                time.sleep(0.1)
                self.robot.send(f"/blink {300*0.9}")
            elif n["level"]>1:
                self.robot.send(f"/nod 10 {100*n["level"]} {n["level"]} {priority}") 
                for _ in range(n["level"]):
                    time.sleep(0.1)
                    self.robot.send(f"/blink {100*0.9}")
        elif n["type"] == "large":
            if n["level"]==1:
                self.robot.send(f"/nod 15 500 {n["level"]} {priority}") 
                time.sleep(0.1)
                self.robot.send(f"/blink {400*0.9}")
            elif n["level"]>1:
                self.robot.send(f"/nod 15 {100*n["level"]} {n["level"]} {priority}") 
                for _ in range(n["level"]):
                    time.sleep(0.1)
                    self.robot.send(f"/blink {100*0.9}")

        time.sleep(0.1)
        keeptime = n["level"]*100*1.3
        command = f"/emotion {e["type"]} {e["level"]} {priority} {keeptime}"
        self.robot.send(command)
        time.sleep(0.1*n["level"]*6)
        el = self._faces["listen"]
        command = f"/emotion {el["type"]} {el["level"]} {priority} {keeptime}"
        self.robot.send(command)

            
    # --- 視線、表情生成 ---

    #視線移動
    def gaze_think(self):
        f = self._faces["think_gaze"]
        print(f)
        self.robot.send(self.create_lookaway(f['type'],f['level']))
        self.waiting = True

    def gaze_engage(self):
        s = self._get_xyz()
        if not s:
            return
        self.robot.send(f"/look {s.x} {s.y} {s.z} 0.5 0.5 0 4 1500")
        self.waiting = False
        self.matching = True

    def gaze_avert(self):
        s = self._get_xyz()
        f = self._faces["speak_gaze"]
        print(f)
        if not s:
            return
        self.robot.send(self.create_lookaway(f['type'],f['level']))
        self.matching = False


    #聞こえない
    def face_cant_hear(self):
        now = time.monotonic()
        if now - self._last_fail_t < self.FAIL_COOLDOWN:
            return
        f = self._faces["cant_hear"]
        self.robot.send(f"/emotion {f['type']} {f['level']} 2 1000") 
        v = self._faces["cant_hear_voice"]
        if v['level'] == 1:
            wave_path = self._filler_choice(True)
            with wave.open(str(wave_path),'rb') as wav_file:
                duration = wav_file.getnframes() / wav_file.getframerate()
            time.sleep(duration)
 
        self._last_fail_t = now
        self.robot.send(f"/emotion neutral 1 5 1000") 


    #聞いている
    def face_listen(self):
        now = time.monotonic()
        if now - self._last_listen_face_t < self.FACE_COOLDOWN:
            return
        f = self._faces["listen"]
        self.robot.send(f"/emotion {f['type']} {f['level']} 2 1000")
        self._last_listen_face_t = now

    def nod_listen(self):
        now = time.monotonic()
        if now - self._last_listen_nod_t < self.LISTEN_NOD_COOLDOWN:# クールダウン
            print(f"[filler_motion_nod] {now} cool_down")
            return
        if now - self._last_meaning_t < self.LISTEN_NOD_MIN_PAUSE:
            print(f"[filler_motion_nod] {now} continue speaking")
            return
        
        tail = self._best_tail_type
        step = self.LISTEN_NOD_STEP

        if tail == "weak":
            step = max(3, self.LISTEN_NOD_STEP - 2)   
        elif tail == "q":
            step = max(2, self.LISTEN_NOD_STEP - 3)
        elif tail == "cont":
            step = self.LISTEN_NOD_STEP + 4           

        print(f"[filler_motion_nod] last_nod_best_clean {self._best_clean}")
        progress = len(self._best_clean) - self._last_nod_best_len
        if progress < step:
            print(f"[filler_motion_nod] {now} don't progress meaning")
            return

        print(f"[filler_motion] {now} nod")
        self._create_listen_nod()

        self._last_listen_nod_t = now
        self._last_nod_best_len = len(self._best_clean)


    #話はじめ
    def face_speak(self):
        now = time.monotonic()
        if now - self._last_speak_face_t < self.FACE_COOLDOWN:
            return
        f = self._faces["speak_face"]
        self.robot.send(f"/emotion {f['type']} {f['level']} 2 1000")
        self._last_speak_face_t = now

    #話し中
    def set_speak_face(self, face_type: str, level: int):
        if face_type == "neutral":
            return
        self.robot.send(f"/emotion {face_type} {level} 2 1000")

    def do_bow(self, kind: str):
        if kind == "small":
            self.robot.send("/bow 10 500 3")
        elif kind == "deep":
            self.robot.send("/bow 20 1000 3")

    def do_between_sentence_gaze(self, gaze_type: str, level: float):
        cmd = self.create_lookaway(gaze_type, level)
        if cmd:
            self.robot.send(cmd)

    def do_end_gaze_return(self):
        self.gaze_engage()

    #考え中    
    def face_wait(self):
        now = time.monotonic()
        if now - self._last_wait_face_t < self.FACE_COOLDOWN:
            return
        f = self._faces["think"]
        self.robot.send(f"/emotion  {f['type']} {f['level']} 2 1000")
        self._last_wait_face_t = now

    #理解
    def face_understand(self):
        now = time.monotonic()
        if now - self._last_wait_face_t < self.FACE_COOLDOWN:
            return
        f = self._faces["understand"]
        self.robot.send(f"/emotion  {f['type']} {f['level']} 2 1000")

    def nod_understand(self):
        if self.noding :
            return
        self.noding = True 
        v = self._faces["understand_voice"]
        n = self._faces["understand_nod"]

        if not self.fixed:
            if v['level'] == 1:
                self._filler_choice()

        self.robot.send(f"/nod {n['level']} 400 1 3")
        time.sleep(0.1)
        duration = 0.4*1000*0.9
        self.robot.send(f"/blink {duration}")

    # --- 入力イベント ---
    def on_interim(self, text: str):
        print("[interium]")
        now = time.monotonic()
        self.last_interim_t = now
        self.last_interim_text = text

        clean = self._clean_interim(text)

        # 内容が進んだ（bestより伸びた）ときだけ meaning を更新
        if len(clean) > len(self._best_clean):
            self._best_clean = clean
            print(f"[interium]best_clean {self._best_clean}")
            self._last_meaning_t = now
            self._best_tail_type = self._classify_tail(clean)

    def on_final(self):
        # final受信 → GPT待ちへ（視線はTHINKへ）
        print("[final]")
        self.gpt_thinking = True
        self.gaze_think()
        self.face_wait()
        self.last_interim_text = ""
        self._best_clean = ""
        self._last_nod_best_len = 0

    def on_gpt_done_before_tts(self):
        # 話し出し直前に視線を戻す
        print("[before_tts]")
        self.gpt_thinking = False
        self.noding =False
        self.tts_playing = True
        self.tts_near_end_engage = False
        self.gaze_engage()
        self.face_speak()

    def on_tts_done_after_playback(self):
        print("[tts finish]")
        self.tts_playing = False
        self.tts_near_end_engage = False
        self.fixed = False

    def on_tts_near_end(self):
        print("[tts near end] engage gaze")
        self.tts_near_end_engage = True
        self.gaze_engage()

    def on_interrupt(self):
        self.robot.send(f"/emotion neutral 1 6 1000")

    def on_fixed(self):
        self.fixed = True

    # --- 周期更新（interimが途切れた/actだけ立ってる等） ---
    def tick(self):
        self._reload_face_cfg_if_needed()
        now = time.monotonic()
        act = self._get_act()
        print(f"[tick] now:{now} act:{act}")
        # print(f"[tick] last_interim_t:{self.last_interim_t}")

        interim_recent = (now - self.last_interim_t) <= self.INTERIM_OK_interval
        interim_stale = (now - self.last_interim_t) >= self.INTERIM_FAIL_interval
        # #print(f"[tick] interim_recent:{interim_recent}")
        # print(f"[tick] interim_stale:{interim_stale}")

        if act >= 2:
        #### actが0→2以上になった(話はじめた)瞬間を検出して時刻を記録(1は物音とかでも反応しちゃう)
            if self._prev_act < 2:
                self._act_on_t = now
                self._last_listen_nod_t = now
            # print(f"[tick] act_on_t:{self._act_on_t}")
            self._prev_act = act

            #### 話し始め直後の猶予期間は、interimが来なくても Suspicion を出さない
            in_grace = (now - self._act_on_t) < self.ASR_GRACE_ON_SPEECH
            # print(f"[tick] in_grace:{in_grace}")
            # print(f"[tick] interim_stale:{interim_stale}")

            if interim_stale and (not in_grace) and (not self.tts_playing) and (not self.gpt_thinking):
                #### 猶予を超えてもinterimが来ない → 聞き取れない表情, interium_textがある場合はこっちにならない
                print("[tick_result] act>=1 face_cant_hear")
                self.face_cant_hear()
            else:
                #### 聞いている
                print("[tick_result] face_listen")
                self.face_listen()
                self.nod_listen()

            if not self.waiting:
                    pass
        else:
            self._prev_act = act
            since_act_on = now - self._act_on_t
            in_grace = (now - self._act_on_t) < self.ASR_GRACE_ON_SPEECH
            # print(f"[tick] in_grace:{in_grace}")

            if self.tts_playing:
                print("[tick_result] speak")
                self.face_speak()
            elif self.fixed:
                print("[tick] fixed")
                self.nod_understand()
                self.face_understand()
            elif (interim_recent or self.gpt_thinking) and (not interim_stale):
                print("[tick_result] else")
                self.nod_understand()
                self.face_understand()
                time.sleep(0.3)
                self.gaze_think()
                self.face_wait()
            elif interim_stale and (not in_grace) and since_act_on<4.0:
                print("[tick_result] act==0 face_cant_hear")
                self.face_cant_hear()
                

    

#もう使わない
    def gaze_speak(self):
        now = time.monotonic()
        match = self._faces["speak_gaze_match"]
        matchtime = match["level"]
        avert = self._faces["speak_gaze_avert"]
        averttime = avert["level"]

        if now - self._last_gaze_match_t < matchtime:
            self.gaze_engage()
            print("[gaze_apeak] matichingtime")
            return
        if now - self._last_gaze_avert_t < averttime:
            self.gaze_avert()
            print("[gaze_apeak] avertingtime")
            return
        if self.matching:
            now = time.monotonic()
            self.gaze_avert()
            self._last_gaze_avert_t = now
            print("[gaze_apeak] avert")
        else:
            now = time.monotonic()
            self.gaze_engage()
            self._last_gaze_match_t = now
            print("[gaze_apeak] match")