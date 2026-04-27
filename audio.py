from __future__ import annotations

import asyncio

from .audio import AudioIO, Utterance, VADSegmenter
from .config import AgentConfig
from .providers import OpenAIProvider


class VoiceAgent:
    def __init__(self, cfg: AgentConfig) -> None:
        self.cfg = cfg
        self.audio = AudioIO(
            sample_rate=cfg.sample_rate,
            channels=cfg.channels,
            frame_ms=cfg.frame_ms,
        )
        self.segmenter = VADSegmenter(
            sample_rate=cfg.sample_rate,
            frame_ms=cfg.frame_ms,
            aggressiveness=cfg.vad_aggressiveness,
            silence_timeout_ms=cfg.silence_timeout_ms,
            min_speech_ms=cfg.min_speech_ms,
        )
        self.provider = OpenAIProvider(
            stt_model=cfg.stt_model,
            llm_model=cfg.llm_model,
            tts_model=cfg.tts_model,
            tts_voice=cfg.tts_voice,
            system_prompt=cfg.system_prompt,
        )
        self.utterance_queue: asyncio.Queue[Utterance] = asyncio.Queue(maxsize=8)

    async def run(self) -> None:
        capture_task = asyncio.create_task(
            self.audio.capture_utterances(self.segmenter, self.utterance_queue)
        )
        print("Voice agent live. Speak naturally; press Ctrl+C to stop.")

        try:
            while True:
                utterance = await self.utterance_queue.get()
                await self._handle_utterance(utterance)
        finally:
            capture_task.cancel()

    async def _handle_utterance(self, utterance: Utterance) -> None:
        loop = asyncio.get_running_loop()
        user_text = await loop.run_in_executor(
            None,
            self.provider.transcribe_pcm16,
            utterance.pcm16,
            utterance.sample_rate,
        )
        if not user_text:
            return

        print(f"You: {user_text}")
        response_text = await loop.run_in_executor(None, self.provider.respond, user_text)
        if not response_text:
            return
        print(f"Agent: {response_text}")

        tts_pcm = await loop.run_in_executor(None, self.provider.synthesize_pcm16, response_text)
        await loop.run_in_executor(None, self.audio.play_pcm16, tts_pcm)
