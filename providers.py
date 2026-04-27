from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class AgentConfig:
    sample_rate: int = 16000
    channels: int = 1
    frame_ms: int = 20
    vad_aggressiveness: int = 2
    silence_timeout_ms: int = 900
    min_speech_ms: int = 350

    stt_model: str = os.getenv("STT_MODEL", "gpt-4o-mini-transcribe")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4.1-mini")
    tts_model: str = os.getenv("TTS_MODEL", "gpt-4o-mini-tts")
    tts_voice: str = os.getenv("TTS_VOICE", "alloy")
    app_name: str = os.getenv("APP_NAME", "vtr.io AI Agent")
    company_name: str = os.getenv("COMPANY_NAME", "vtr.io")
    logo_url: str = os.getenv("LOGO_URL", "")
    accent_color: str = os.getenv("ACCENT_COLOR", "#1f6feb")
    accent_color_2: str = os.getenv("ACCENT_COLOR_2", "#11a36f")
    whatsapp_url: str = os.getenv("WHATSAPP_URL", "https://wa.me/8978237578")
    calendly_url: str = os.getenv("CALENDLY_URL", "")
    client_api_key: str = os.getenv("CLIENT_API_KEY", "")
    admin_key: str = os.getenv("ADMIN_KEY", "")
    max_history_turns: int = int(os.getenv("MAX_HISTORY_TURNS", "6"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

    system_prompt: str = (
        "You are a professional, concise AI voice assistant. "
        "Answer clearly, actionably, and avoid unnecessary verbosity."
    )
