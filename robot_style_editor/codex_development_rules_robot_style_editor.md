# Codex 開発ルール: robot_style_editor

## 0. 前提

このプロジェクトは `chatbot/robot_style_editor` 配下の Tkinter ベースの UI で、ロボットの話し方・表情・視線・相槌・音声タイミングなどを調整するための研究用エディタである。

目的は「研究参加者が違いを理解しながら選べる UI」を作ることなので、単に動けばよいのではなく、UI の統一感・保存形式・共通部品化・後から調整しやすい構造を重視する。

---

## 1. ディレクトリ構造

新しいファイルを作るときは、以下の分類に従う。

```text
chatbot/robot_style_editor/
├─ config.py
├─ config_face.py
├─ main.py
├─ launcher.py
├─ profile_store.py
├─ face_preset_store.py
├─ ui_style.py
│
├─ panels/
│  ├─ face_editor_panel.py
│  ├─ gaze_direction_panel.py
│  └─ mic_activity_panel.py
│
├─ audio/
│  ├─ response_delay_player.py
│  ├─ speed_audio_player.py
│  ├─ voice_activity_source.py
│  └─ wav_silence.py
│
├─ clients/
│  ├─ robot_command_client.py
│  └─ tts_client.py
│
└─ tabs/
   ├─ *_tab.py
   └─ ...
```

### 配置ルール

- `tabs/`: 各設定タブ本体。
- `panels/`: 複数タブで使う共通 UI 部品。
- `audio/`: WAV 再生、速度変更、マイク入力、無音 trim など音声・音響処理。
- `clients/`: ロボットコマンド、TTS サーバーなど外部通信。
- 直下: `config.py`, `config_face.py`, `main.py`, `profile_store.py`, `face_preset_store.py`, `ui_style.py` などアプリ全体に関わるもの。

`face_preset_store.py` は直下を正とする。

---

## 2. import 方針

整理後の構造を前提に import する。

```python
from ..panels.mic_activity_panel import MicActivityPanel
from ..panels.face_editor_panel import FaceEditorPanel
from ..panels.gaze_direction_panel import GazeDirectionPanel

from ..audio.response_delay_player import ResponseDelayPlayer
from ..audio.wav_silence import trim_silence_to_temp_wav

from ..clients.robot_command_client import RobotCommandClient
from ..clients.tts_client import TTSClient
```

古い直下 import に戻さない。

---

## 3. UI 共通ルール

### 3.1 `ui_style.py` を使う

タブ内で色・フォント・余白・基本スタイルを直接指定しすぎない。基本的に `ui_style.py` の共通部品を使う。

例:

```python
from .. import ui_style as ui

ui.frame(...)
ui.label(...)
ui.bordered_frame(...)
ui.radio(...)
ui.sub_button(...)
ui.action_button(...)
ui.scale(...)
```

### 3.2 スライダー

スライダーは `ui.scale()` を使う。タブ側で `resolution`, `bg`, `fg`, `troughcolor`, `highlightthickness`, `bd` などを重複指定しない。

既存の `ui.scale()` は以下の共通設定を持っている前提。

```python
resolution=0.05
showvalue=False
bg=COLORS["panel"]
fg=COLORS["text"]
troughcolor=COLORS["soft_border"]
highlightthickness=0
bd=0
```

### 3.3 スクロール領域

スクロールが必要な画面では、タブや Panel 内に `Canvas + Scrollbar + create_window` を直接書かない。
共通部品として `ui_style.py` の `ui.scrollable_frame(...)` を使う。

```python
content = ui.scrollable_frame(
    page,
    pady=(ui.SPACING["section_y"], 0),
)
```

返り値の `content` に、各セクションやカードを `pack` / `grid` していく。

---

## 4. タブ UI の標準レイアウト

### 4.1 基本構成

各タブは基本的に以下の構成にする。

```text
ページタイトル
説明文
設定エリア
保存して次へ
```

「保存して次へ」は常に右下寄せにする。

### 4.2 上部タブ名

Notebook のタブ名は要素名だけにする。

例:

```text
話者
敬語
親しみ
語彙
長さ
話速
文間
返答
考える姿
聴く姿
理解
```

「〜を選ぶ」「〜設定」など長い名前にしない。

### 4.3 選択肢が「低・中・高 + その他」の場合

低・中・高の3カードを横並びにし、その下に「その他」を1段で置く。

### 4.4 選択肢カードの例文

各選択肢カードには、参加者が違いを理解できるように例文を常時表示する。

例文は無難に寄せすぎず、違いが分かる程度にやや極端にしてよい。

### 4.5 読み上げ文と再生ボタン

読み上げる文入力欄と再生ボタンは同じ高さに配置する。
「保存して次へ」だけ少し下に置く。
画面最下部固定ではなく、選択肢の下に続けて配置する。

---

## 5. 画面切り替えルール

### 5.1 共通 Panel に遷移する場合

`FaceEditorPanel` や `GazeDirectionPanel` へ遷移するタブは、必ず以下の構造を持つ。

```python
def clear_views(self):
    for child in self.winfo_children():
        child.destroy()


def build_main_view(self):
    self.clear_views()
    self.build_ui()
```

`__init__()` ではできれば `self.build_main_view()` を呼ぶ。

`FaceEditorPanel` に渡す `on_back` は `self.build_ui` ではなく、原則 `self.build_main_view` にする。

```python
editor = FaceEditorPanel(
    self,
    robot_client=self.robot_client,
    on_back=self.build_main_view,
    on_saved=self.on_custom_face_saved,
)
```

`on_back=self.build_ui` にすると、既存画面を消さずに UI が重なってバグる。

### 5.2 `after()` は使わない

この環境では Tkinter の `after()` を使うと動かなくなるケースがあった。
そのため、今後のコード提案では `after()` を使わない。

どうしても `after()` が必要な場合だけ、その理由・問題点・代替案を明示して相談する。

既存コードに残っている `after()` も置換対象として扱う。
特に `MicActivityPanel` のメーター更新・状態更新に使われている `after()` は、今後の修正で `after()` に依存しない実装へ置き換える。

---

## 6. 表情・視線の「その他」ルール

### 6.1 表情のあるタブには必ず「その他」を入れる

ユーザーが明示し忘れていても、表情選択があるタブには必ず「その他」を入れる。

「その他」はタブ内に直接編集 UI を書かず、共通の `FaceEditorPanel` に遷移する。

```python
from ..panels.face_editor_panel import FaceEditorPanel
```

保存時は `robot_speech_profile.json` に表情軸データ本体を書かず、表情名を保存する。

例:

```json
"face": {
  "id": "custom:neutral21",
  "label": "neutral21",
  "type": "neutral21",
  "level": 1,
  "custom": true
}
```

表情データ本体は別の face config / preset store 側で管理する。

### 6.2 視線の「その他」は `GazeDirectionPanel`

視線のその他は、タブ内に9方向UIを直接書かない。
必ず共通の `GazeDirectionPanel` に遷移する。

保存時は「その他」であることを特別に保存しない。
他の視線選択肢と同じ形式で、選択された視線データだけを保存する。

```python
from ..panels.gaze_direction_panel import GazeDirectionPanel, find_gaze_option
```

---

## 7. 保存ルール

各タブは `profile_store.set(..., auto_save=True)` で保存する。
基本的にすべて `auto_save=True` とし、`auto_save=False` は使わない。

基本構成:

```python
def get_current_data(self):
    return {...}


def save_selection_only(self, update_status=True):
    self.profile_store.set(
        "some_key",
        self.get_current_data(),
        auto_save=True,
    )
    if update_status:
        self.status_var.set("保存しました")


def save_and_next(self):
    self.save_selection_only()
    if self.on_saved is not None:
        self.on_saved()
```

`robot_speech_profile.json` には、実行時に必要な選択結果だけを保存する。
巨大なUI状態や表情の全軸データなどは入れない。

---

## 8. 定数管理ルール

調整値・固定値をタブ内にベタ書きしない。

例:

```python
0.15
0.2
0.65
1.2
0.003
800
3000
```

このような値は、原則として `config.py` または `config_face.py` に入れる。

### 使い分け

- `config.py`: 音声・マイク・時間・アプリ全体設定。
- `config_face.py`: 表情・視線・うなづき・ロボット動作系。
- `ui_style.py`: 色・フォント・余白・枠線などUI見た目の共通設定。

研究条件、保存値、ロボット動作、音声タイミングに関わる値は `config.py` / `config_face.py` に寄せる。
単なる Tkinter レイアウト寸法や見た目の値は、まず `ui_style.py` の共通部品を使う。
必要に応じて `ui_style.py` 側に UI 用定数を追加してよい。

ただし、完全にダミー用で本番に入れない一時ファイルは、そのファイル内で完結してよい。

---

## 9. ロボットコマンド仕様

### 9.1 `/nod`

`/nod` の形式は以下。

```text
/nod <amplitude> <duration> <times> <priority>\n
```

`level` は存在しない。

正しい関数例:

```python
def send_nod(self, amplitude: int, duration: int, times: int, priority: int):
    self.send(f"/nod {amplitude} {duration} {times} {priority}")
```

呼び出し例:

```python
self.robot_client.send_nod(
    amplitude=15,
    duration=500,
    times=1,
    priority=3,
)
```

### 9.2 表情

基本形式:

```text
/emotion <type> <level> <priority> <keeptime>
```

### 9.3 顔軸

基本形式:

```text
/movemulti5 <axis> <value 0-255> <velocity> <priority> <keeptime>
```

### 9.4 視線

`lookaway` 系は既存の `RobotCommandClient.send_lookaway()` を使う。

---

## 10. Mac 開発時のダミーサーバー

MacでUIだけ開発する場合、`robot_command_client.py` は本番用のままにする。
代わりに TCP ダミーサーバーを立てる。

`robot_command_client.py` は HTTP POST ではなく TCP socket で送る作りなので、ダミーも TCP サーバーにする。

例ファイル:

```text
chatbot/robot_style_editor/clients/dummy_robot_server.py
```

このダミーは本番用ではないため、定数を `config.py` に入れず、1ファイルで完結してよい。

---

## 11. 音声・WAV処理ルール

### 11.1 WAVは再生前に無音trimする

文間や相槌のタイミングを正確に扱うため、WAV再生前には前後の無音を削る。

```python
from ..audio.wav_silence import trim_silence_to_temp_wav
```

既存の `tts_client.py` にある以下のような関数を使う。

```python
play_preview_wav_trimmed_and_get_duration(...)
```

### 11.2 タブ内に再生ロジックを増やしすぎない

WAV再生、速度変更、文間再生、返答遅延再生は `audio/` または `clients/tts_client.py` に寄せる。

タブ内では、基本的に以下のように呼ぶだけにする。

```python
self.tts_client.play_preview_wav(...)
self.tts_client.play_wav_pair_with_pause(...)
self.response_player.schedule_response(...)
```

---

## 12. マイクテストルール

マイク入力 UI は共通の `MicActivityPanel` を使う。

```python
from ..panels.mic_activity_panel import MicActivityPanel
```

タブごとにマイクUIを直接書かない。

`MicActivityPanel` は以下を担当する。

```text
- 認識開始 / 認識終了ボタン
- 音量バー
- 状態表示
- volume / speaking の取得
- on_speech_start / on_speech_end callback
```

タブ側は「検出後に何をするか」だけを書く。

---

## 13. 相槌テストの扱い

相槌テストは現状、音量ベースの簡易検出であり、自然なタイミングではまだ不安定。

現時点では時間をかけすぎず、余裕があれば後で直す課題として扱う。

課題:

```text
- 音量ベースだけではタイミングが遅い
- 相槌量の違いが体感に出にくい場合がある
- 自然に行うには VAP / 相槌予測モデルの導入が必要かもしれない
```

今後の修正では、相槌のタイミング予測とUI設定値を分離して考える。

---

## 14. 既存タブの思想

### 14.1 話し方系

話者、敬語、親しみ、語彙、長さは、選択肢ごとに例文を常時表示する。

親しみ・語彙・長さなどは、話者・敬語・親しみ・語彙など前段の選択を反映して例文を変える。

### 14.2 長さタブ

長さタブでは敬語レベルを変えない。
語尾の丁寧さは敬語タブに任せる。

長さの例は以下の2種類を見せる。

```text
例1：同じ情報を言い回しで長くする例
例2：少し補足を足して長くする例
```

### 14.3 文間タブ

文間タブでは以下を調整する。

```text
- 文と文の間の秒数
- 文間の視線移動
```

文間視線は、横・上・下・その他。
その他は `GazeDirectionPanel`。

文間再生では、1文目終了後、文間に入ったタイミングで視線移動 callback を呼ぶ。

---

## 15. 発話意図タブ

発話意図ごとのタブでは、意図ごとの文章、テクニック、声色をまとめて調整する。

挨拶・説明など、細かなフェーズごとの調整タブは、基本の話し方設定と姿勢・理解系の設定が終わった後に置く。
Notebook 上では `理解` の後に配置する。

定数が増える場合は `config_intention.py` に分けてよい。
発話意図ごとのテクニック定義、声色プリセット、文章生成用テンプレート、声色変換マップなどは `config_intention.py` に置く。

### 15.1 文章欄

発話意図タブの文章は、最終的には研究参加者が入力・調整する前提にする。
自動生成文は初期候補として使う。

「最初の文」と「全文」のような二重管理は避ける。
保存・読み上げに使う本文欄を正とする。

### 15.2 参照中の話し方設定

発話意図タブでは、文章生成に使っている前段設定を UI に表示する。

挨拶・説明などの発話意図タブでは、少なくとも以下を表示する。

```text
- 話者
- 敬語
- 親しみ
- 語彙
- 長さ
```

文章生成では、話者・敬語・親しみ・語彙・長さをすべて反映する。

親しみが高い場合は話者ごとに語尾を変える。

```text
- のぞみ: 「〜」など柔らかく伸ばす語尾
- けんた: 「っす」「っすね」「っすか」など、接客で許容できる範囲の砕けた語尾
```

カジュアルでは敬語を使わない。
`config.py` の既存例文に寄せて、「今日はどうしたの？」などの文体にする。

### 15.3 挨拶テクニック

挨拶で使うテクニックは、基本的に以下に絞る。

```text
- 季節
- 時刻
- 配慮
```

テクニックは複数選択できるようにする。
複数選択時は、単純に文を積み上げない。
選択された組み合わせとして自然な文章へ再生成する。

例:

```text
季節 + 時刻 + 配慮
→ 今日は過ごしやすい気候ですね。お仕事帰りでしたら、無理のない範囲でゆっくりご案内します。
```

### 15.4 説明テクニック

説明タブでも、挨拶タブと同じく、話者・敬語・親しみ・語彙・長さをすべて反映して文章を生成する。
どの設定を参照して文章を生成しているか、UI 上に常時表示する。

説明で使うテクニックは数が多いため、選択された文を単純に積み上げない。
複数選択時は、説明として自然な順序に整理してから文章化する。

基本の並びは以下を目安にする。

```text
許可・目的
→ 共感
→ 本文
→ 根拠・専門性
→ 言い換え・要約
→ 手順
→ 先回り提案
```

短い文章では、選択されたテクニックのうち効果が伝わる代表要素だけを残し、極端に短くする。
長い文章では、根拠・手順・補足を自然につなげて、説明として破綻しないようにする。

### 15.5 声色

声色の「その他」は、詳細編集用の共通 Panel に分ける。
発話意図タブ内に直接、声色の詳細編集 UI を書き込まない。

詳細編集 Panel は `panels/` に置き、他の発話意図タブでも再利用できるようにする。

詳細編集 Panel では、以下の7項目を個別調整できるようにする。

```text
- volume
- rate
- pitch
- emphasis
- joy
- anger
- sadness
```

また、詳細編集 Panel では以下の抽象声色を読み込み、7項目へ反映してから微調整できるようにする。

```text
- 親しみ
- 落ち着き
- テンション
```

`robot_console.py` の voice panel と同じ考え方で、抽象声色の重ねがけを許容する。

詳細編集 Panel では、現在のタブ本文を受け取り、その文章を使って TTS 試聴できるようにする。
事前 WAV を大量に用意するのではなく、必要に応じて都度 TTS で作成してよい。

---

## 16. Codexに依頼するときの進め方

Codexに依頼するときは、以下の形で依頼するとよい。

```text
目的:
- 何を作りたいか

対象ファイル:
- chatbot/robot_style_editor/tabs/xxx_tab.py
- chatbot/robot_style_editor/config_face.py

守ってほしいルール:
- この開発ルールに従う
- 定数は config.py / config_face.py に入れる
- 共通UIは panels/ に置く
- after() は使わない
- 表情がある場合は必ず「その他」を入れ、FaceEditorPanel を使う

実装内容:
- UI項目
- 保存JSON形式
- ロボットコマンド
- マイクテストの有無
```

大きな修正では差分が見づらくなるので、複数関数にまたがる大きな変更はファイル単位で提案してよい。
小さな変更や新規ファイル追加だけなら、どこをどう変更するかを明示する。

---

## 17. 優先順位

実装時の優先順位は以下。

```text
1. 既存UIと見た目・操作感を揃える
2. 保存JSONを壊さない
3. 共通化できるものは panels/audio/clients に寄せる
4. 定数を config に寄せる
5. Mac開発時にロボット未接続でも落ちないようにする
6. 本番実機用の robot_command_client.py は極力壊さない
```

---

## 18. 実機連携と UI 停止を避けるルール

実機連携では、Mac 上で動く処理よりもフリーズ・タイミングずれ・名前解決エラーが起きやすい。
次のプロダクトでも、以下を前提に設計する。

### 18.1 lock 内で外部処理を呼ばない

`threading.Lock` は共有状態を一瞬だけ守るために使う。
lock の中で以下を呼ばない。

```text
- UI更新
- Tkinter event_generate
- ロボットコマンド送信
- TTS生成
- WAV再生
- HTTP / socket 通信
- ファイル保存
- 任意の callback
```

悪い例:

```python
with self._lock:
    self._state.speaking = True
    self.on_start(now)  # この先でUI・ロボット送信に広がるため危険
```

良い例:

```python
callback = None
callback_t = None

with self._lock:
    self._state.speaking = True
    callback = self.on_start
    callback_t = now

if callback is not None:
    callback(callback_t)
```

lock の中では `speaking`, `started_at`, `ended_at`, `volume` などの状態更新だけを行う。
外部処理は lock の外に出す。

### 18.2 callback は軽い入口にする

`on_speech_start` / `on_speech_end` のような callback は、直接重い処理をしない。
できればイベントキューに積み、実演制御側の worker が順番に処理する。

特に短い発話では `act=1 -> act=0` がすぐ起きる。
開始処理中に終了処理が来ても破綻しないようにする。

### 18.3 act は状態変化だけを見る

実環境では `robot_act` が高頻度で更新される。
毎回 UI 更新やロボット送信をしない。

基本は以下だけを見る。

```text
- active=False -> True: 発話開始
- active=True -> False が一定時間続く: 発話終了
```

`act >= 1` の間ずっとメーターやUIを更新し続けると、UIが詰まりやすい。

### 18.4 UI スレッドへは安全に通知する

worker thread から Tkinter UI を直接触らない。
`queue.SimpleQueue` などにイベントを積み、UIスレッドで処理する。

`event_generate` だけで通知が届かないケースがあるため、必要に応じて以下の方式を使う。

```text
- queue にイベントを積む
- os.pipe() に1byte書く
- createfilehandler でUIスレッド側の処理を起こす
```

接客例やデフォルト実演のように、TTS生成完了後に画面遷移する処理では、`done` イベントが必ず UI に届く設計にする。

### 18.5 重いタブ・重いUIは遅延生成する

実環境PCでは、使っていないタブまで全て初期化すると落ちやすい。
以下は遅延生成する。

```text
- 接客例
- 詳細要望一覧
- デフォルトで話す
- 実演UI
- TTS生成処理
```

「画面を開いた時」「ボタンを押した時」に初期化する。
アプリ起動時に全て作らない。

### 18.6 描画は選択中の場面だけにする

接客例など場面数が多い UI では、全場面を一度に描画しない。
選択中の店舗・選択中の場面だけを描画する。

大量の会話カード、DA表示、履歴表示を同時に作るとUIが重くなる。

### 18.7 実演UIとTTS生成はボタン押下後に初期化する

ロボット実演の準備は重い。
画面表示時ではなく、ユーザーが「試す」「実演準備」などを押した時に開始する。

準備中は以下を表示する。

```text
- 生成中メッセージ
- 件数 progress
- indeterminate spinner
- エラー時の復帰先
```

TTS生成が終わったら、必ず実演画面へ遷移する `done` イベントをUIスレッドで処理する。

### 18.8 WAVは trim を前提にする

WAV末尾の無音をそのまま使うと、文間・返答間・発話終了タイミングがずれる。
実演や文間確認では trim できるようにする。

```text
- 再生前にtrimする
- trimするかどうかはUIで選べるようにする
- キャッシュする音声はtrim済みを保存できるようにする
```

### 18.9 環境切り替えは最初に選べるようにする

実環境とMac上では以下が違う。

```text
- mic: robot_act / Mac mic
- TTS: 実TTSサーバー / dummy TTS
- robot command: 実機TCP / dummy TCP
- audio playback: ノートPC / ニコラPC
```

起動時または画面内で明示的に選べるようにする。
デフォルトは研究で使う安全な設定にする。

### 18.10 .env とプリセットの上書きに注意する

`.env` にIPやURLを書いても、起動時の環境プリセットで上書きされると意味がない。

実機接続先を `.env` で指定する場合は、以下に注意する。

```text
- .env を読み込む場所はアプリ内で明示する
- 環境選択後に .env の値が上書きされないか確認する
- 実験直前は現在のURLをログに出す
```

TTSやニコラPC連携では、名前解決できないホスト名よりIP指定を優先する。

例:

```text
ROBOT_TTS_PLAY_URL=http://192.168.x.x:15003/speak
ROBOT_TTS_PREPARE_URL=http://192.168.x.x:15003/prepare
ROBOT_TTS_PLAY_AUDIO_URL=http://192.168.x.x:15003/play
```

### 18.11 音声再生場所は研究条件として選べるようにする

ノートPCから音が出る場合と、ニコラPC側から音が出る場合では、参加者の印象が変わる。
そのため、音声再生先はUIで選べるようにする。

```text
- ノートPCで再生
- ニコラPCで再生
```

デフォルトはノートPCなど、動作確認しやすい安全な設定にする。

ニコラPCで再生する場合は、ノートPCからテキスト・TTS instruction・話者を送り、ニコラPC側でTTS生成とWAV再生を行う。
「生成」と「再生」を分け、実演タイミングに合わせて `/play` できる設計にする。

### 18.12 実機連携はログを入れやすくする

実機ではどこで止まったか分かりにくい。
以下の境界には短いログを入れられるようにする。

```text
- act active 変化
- speech_start / speech_end callback 前後
- ロボットコマンド送信前後
- TTS生成開始 / 完了
- UI queue に done を積んだ時
- UI queue の done を処理した時
```

ログは `flush=True` を付ける。
実験後に不要になった詳細ログは、必要に応じて整理する。

### 18.13 フッターは先に高さを確保する

画面が低いPCでは、Notebook が高さを取りすぎて保存ボタンや音声再生先が見えなくなる。

フッターを使う場合は、先に `side="bottom"` で確保し、その後に Notebook を `side="top", expand=True` で置く。

```python
footer.pack(side="bottom", fill="x")
notebook.pack(side="top", fill="both", expand=True)
```

低い画面では、`ui_style.configure_density()` でフォント・余白・タブpadding・ボタン高さを圧縮する。

---

## 19. 研究データ・店舗別設定・比較UIのルール

### 19.1 研究データは上書きしない

研究参加者の設定は結果データなので、既存ファイルを不用意に上書きしない。
新規ユーザーはユーザー名を先に入力させ、ユーザーごとのフォルダを作る。

例:

```text
save_json/
└─ 参加者A/
   ├─ hotel.json
   ├─ museum.json
   ├─ fast_food.json
   ├─ apparel.json
   └─ electronics_store.json
```

### 19.2 店舗ごとにプロファイルを分ける

ホテル、美術館、ファストフード、アパレル、家電量販店では、望まれる話し方が異なる。
同じユーザーでも店舗ごとに設定を分ける。

新しいユーザーを開始したら、以下の流れにする。

```text
ユーザー名入力
→ 店舗選択
→ その店舗のデフォルト会話を試す
→ 話し方設定
→ 接客例生成・実演
→ 保存
```

### 19.3 DAは雑談以外を全店舗で設定する

接客場面で使う発話意図は、店舗ごとに多少違って見えても、基本設定としては共通にする。

設定対象:

```text
- 挨拶
- 説明
- 質問
- 承諾
- 要求
- 謝罪
- 感謝
- フィラー
```

雑談は通常の接客例とは性質が異なるため、店舗別の接客場面設定では原則対象外にする。

### 19.4 生成履歴はプロファイル本体と分ける

接客例の生成履歴はプロファイル本体に直書きしない。
必要に応じて companion file として保存する。

プロファイル本体には、その店舗で最終的に選ばれた話し方設定を保存する。
接客例の生成案・修正履歴・詳細要望は、別データとして扱う。

### 19.5 比較UIは本体UIと分ける

複数ユーザーの話し方比較は重くなりやすい。
本体の設定UIに入れず、別UIとして作る。

比較UIの流れ:

```text
ユーザー比較
→ 店舗選択
→ 場面選択
→ ユーザー選択
→ デフォルト + 最大3ユーザーを横並び表示
→ 必要な話し方だけ試す
```

比較UIでは、最大4列を基本にする。

```text
1. デフォルト
2. ユーザー1
3. ユーザー2
4. ユーザー3
```

### 19.6 比較UIの実演は既存接客例UIを再利用する

比較画面で試すときは、新しく実演ロジックを書かない。
既存の `ExampleSceneTab` など、接客例で使っているUI・TTS生成・実演処理を再利用する。

比較UI側は以下だけを担当する。

```text
- ユーザーフォルダ/JSONの読み込み
- 店舗と場面の選択
- デフォルトとユーザー設定の横並び表示
- 試す対象を選んで接客例UIを開く
```
