import logging
from dotenv import load_dotenv
from typing import AsyncIterable

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, JobContext
from livekit.plugins import noise_cancellation, silero, deepgram, google
from logging import getLogger
from livekit.agents import ModelSettings
from livekit import rtc

logger = getLogger("agents logs")
load_dotenv(".env")

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis or symbols.
            You are curious, friendly, and have a sense of humor."""
        )
    
    async def tts_node(
        self,
        text: AsyncIterable[str],
        model_settings: ModelSettings,
    ) -> AsyncIterable[rtc.AudioFrame]:
        """
        Pipeline node: Logs agent response text before TTS synthesis.
        Delegates to default TTS after logging.
        """
        # Log text chunks as they arrive
        async def log_text_chunks() -> AsyncIterable[str]:
            async for chunk in text:
                logger.info(f"🔊 Agent Response: {chunk}")
                yield chunk
        
        # Delegate to default TTS implementation
        async for frame in Agent.default.tts_node(self, log_text_chunks(), model_settings):
            yield frame
    
    async def on_enter(self) -> None:
        print("Session started. Sending greeting...")
        await self.session.say("Hi Nikhil, how can I help you today?")

async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=deepgram.STTv2(
            model="flux-general-en",
            eager_eot_threshold=0.4,
        ),
        llm=google.LLM(
            model="gemini-2.5-flash",
        ),
        tts=deepgram.TTS(
            model="aura-asteria-en",
        ),
        vad=silero.VAD.load()
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
