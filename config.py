from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass

import numpy as np
import sounddevice as sd
import webrtcvad


@dataclass
class Utterance:
    pcm16: bytes
    sample_rate: int


class VADSegmenter:
    def __init__(
        self,
        sample_rate: int,
        frame_ms: int,
        aggressiveness: int,
        silence_timeout_ms: int,
        min_speech_ms: int,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.vad = webrtcvad.Vad(aggressiveness)

        self.frame_bytes = int(sample_rate * (frame_ms / 1000.0) * 2)
        self.max_silence_frames = max(1, silence_timeout_ms // frame_ms)
        self.min_speech_frames = max(1, min_speech_ms // frame_ms)

        self.pre_roll = deque(maxlen=8)
        self.current_speech: list[bytes] = []
        self.in_speech = False
        self.silence_count = 0

    def push_frame(self, frame: bytes) -> Utterance | None:
        if len(frame) != self.frame_bytes:
            return None

        is_voice = self.vad.is_speech(frame, self.sample_rate)
        self.pre_roll.append(frame)

        if is_voice:
            if not self.in_speech:
                self.in_speech = True
                self.current_speech = list(self.pre_roll)
            else:
                self.current_speech.append(frame)
            self.silence_count = 0
            return None

        if self.in_speech:
            self.current_speech.append(frame)
            self.silence_count += 1

            if self.silence_count >= self.max_silence_frames:
                self.in_speech = False
                speech_frames = self.current_speech
                self.current_speech = []
                self.silence_count = 0

                if len(speech_frames) >= self.min_speech_frames:
                    return Utterance(
                        pcm16=b"".join(speech_frames), sample_rate=self.sample_rate
                    )
        return None


class AudioIO:
    def __init__(self, sample_rate: int, channels: int, frame_ms: int) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_ms = frame_ms
        self.blocksize = int(sample_rate * (frame_ms / 1000.0))

    async def capture_utterances(self, segmenter: VADSegmenter, queue: asyncio.Queue) -> None:
        loop = asyncio.get_running_loop()

        def callback(indata, frames, time_info, status):  # noqa: ANN001
            del frames, time_info
            if status:
                return
            audio = np.clip(indata[:, 0], -1.0, 1.0)
            pcm = (audio * 32767).astype(np.int16).tobytes()
            utt = segmenter.push_frame(pcm)
            if utt is not None:
                loop.call_soon_threadsafe(queue.put_nowait, utt)

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=self.blocksize,
            callback=callback,
        )

        with stream:
            while True:
                await asyncio.sleep(0.1)

    def play_pcm16(self, pcm16: bytes) -> None:
        if not pcm16:
            return
        audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32767.0
        sd.play(audio, samplerate=self.sample_rate, blocking=True)
