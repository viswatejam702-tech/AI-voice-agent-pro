import asyncio
import os

from app.agent import VoiceAgent
from app.config import AgentConfig


def validate_env() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and set your key."
        )


async def main() -> None:
    validate_env()
    cfg = AgentConfig()
    agent = VoiceAgent(cfg)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
