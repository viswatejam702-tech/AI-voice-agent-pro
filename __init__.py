from __future__ import annotations

from io import BytesIO

from openai import OpenAI


class OpenAIProvider:
    def __init__(
        self,
        stt_model: str,
        llm_model: str,
        tts_model: str,
        tts_voice: str,
        system_prompt: str,
    ) -> None:
        self.client = OpenAI()
        self.stt_model = stt_model
        self.llm_model = llm_model
        self.tts_model = tts_model
        self.tts_voice = tts_voice
        self.system_prompt = system_prompt

    def transcribe_pcm16(self, pcm16: bytes, sample_rate: int) -> str:
        wav_bytes = self._pcm16_to_wav(pcm16, sample_rate)
        transcript = self.client.audio.transcriptions.create(
            model=self.stt_model,
            file=("audio.wav", wav_bytes, "audio/wav"),
        )
        return (transcript.text or "").strip()

    def respond(self, user_text: str, conversation: list[dict[str, str]] | None = None) -> str:
        chat_history = conversation or []
        resp = self.client.responses.create(
            model=self.llm_model,
            input=[
                {"role": "system", "content": self.system_prompt},
                *chat_history,
                {"role": "user", "content": user_text},
            ],
        )
        return (resp.output_text or "").strip()

    def synthesize_pcm16(self, text: str) -> bytes:
        with self.client.audio.speech.with_streaming_response.create(
            model=self.tts_model,
            voice=self.tts_voice,
            input=text,
            response_format="pcm",
        ) as response:
            return response.read()

    @staticmethod
    def _pcm16_to_wav(pcm16: bytes, sample_rate: int) -> bytes:
        import wave

        buffer = BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm16)
        return buffer.getvalue()
