from .config import TTS_URL, DEFAULT_INSTRUCTIONS
from chatbot.tts import tts_nikola_data as tts


class TTSClient:
    def __init__(self, url=TTS_URL):
        self.url = url

    def speak(self, text: str, instructions: dict | None = None, person: str | None = None):
        text = text.strip()
        if not text:
            return None

        merged = {
            **DEFAULT_INSTRUCTIONS,
            **(instructions or {}),
        }

        resolved_person = person or merged.get("tts_speaker_change")

        if resolved_person is None:
            return tts.speak_async(
                text=text,
                instructions=merged,
                url=self.url,
            )

        return tts.speak_async(
            text=text,
            instructions=merged,
            url=self.url,
            person=resolved_person,
        )

    def change_speaker_and_speak(self, text: str, speaker: str):
        instructions = {
            **DEFAULT_INSTRUCTIONS,
            "tts_speaker_change": speaker,
        }

        return self.speak(
            text=text,
            instructions=instructions,
            person=speaker,
        )

    def speak_current_speaker(self, text: str, instructions: dict | None = None):
        return self.speak(
            text=text,
            instructions=instructions or DEFAULT_INSTRUCTIONS,
        )