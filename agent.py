import logging
from multiprocessing.util import LOGGER_NAME
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import noise_cancellation, silero, deepgram, google
from logging import getLogger

logger = logging.getLogger("agents logs")

load_dotenv(".env")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis or symbols.
            You are curious, friendly, and have a sense of humor."""
        )
    # async def on_session_started(self, session: AgentSession):
    #     """
    #     Triggered AFTER audio tracks are active.
    #     Safe to speak greeting here.
    #     """
    #     print("Session started. Sending greeting...")
    #     await session.say("Hi Nikhil, how can I help you today...")


async def entrypoint(ctx: agents.JobContext):
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
    await session.say("Hi Nikhil How can i help you today...")
    



if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
