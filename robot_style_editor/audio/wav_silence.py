# chatbot/robot_style_editor/wav_silence.py

from pathlib import Path
import tempfile
import wave
import audioop


def trim_silence_to_temp_wav(
    src_path: Path,
    threshold: int = 400,
    keep_silence_ms: int = 50,
) -> Path:
    """
    WAVの前後の無音を削った一時WAVを作る。
    threshold が小さいほど小さな音も音声として扱う。
    keep_silence_ms は切りすぎ防止のために残す無音。
    """
    src_path = Path(src_path)

    if not src_path.exists():
        raise FileNotFoundError(f"WAV file not found: {src_path}")

    with wave.open(str(src_path), "rb") as wf:
        params = wf.getparams()
        frames = wf.readframes(wf.getnframes())

    sample_width = params.sampwidth
    frame_rate = params.framerate
    channels = params.nchannels

    frame_size = sample_width * channels
    total_frames = len(frames) // frame_size

    if total_frames <= 0:
        return src_path

    chunk_ms = 10
    chunk_frames = max(1, int(frame_rate * chunk_ms / 1000))
    keep_frames = int(frame_rate * keep_silence_ms / 1000)

    def chunk_rms(start_frame: int, end_frame: int) -> int:
        start_byte = start_frame * frame_size
        end_byte = end_frame * frame_size
        chunk = frames[start_byte:end_byte]
        if not chunk:
            return 0
        return audioop.rms(chunk, sample_width)

    start = 0
    while start < total_frames:
        end = min(total_frames, start + chunk_frames)
        if chunk_rms(start, end) > threshold:
            break
        start = end

    end = total_frames
    while end > start:
        chunk_start = max(start, end - chunk_frames)
        if chunk_rms(chunk_start, end) > threshold:
            break
        end = chunk_start

    start = max(0, start - keep_frames)
    end = min(total_frames, end + keep_frames)

    start_byte = start * frame_size
    end_byte = end * frame_size
    trimmed_frames = frames[start_byte:end_byte]

    temp = tempfile.NamedTemporaryFile(
        suffix="_trimmed.wav",
        delete=False,
    )
    temp_path = Path(temp.name)
    temp.close()

    with wave.open(str(temp_path), "wb") as out:
        out.setparams(params)
        out.writeframes(trimmed_frames)

    return temp_path


def trim_silence_to_wav(
    src_path: Path,
    dst_path: Path,
    threshold: int = 400,
    keep_silence_ms: int = 50,
) -> Path:
    temp_path = trim_silence_to_temp_wav(
        src_path=src_path,
        threshold=threshold,
        keep_silence_ms=keep_silence_ms,
    )
    dst_path = Path(dst_path)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    Path(temp_path).replace(dst_path)
    return dst_path
