# import logging
# from dotenv import load_dotenv
# from typing import AsyncIterable

# from livekit import agents
# from livekit.agents import AgentSession, Agent, RoomInputOptions, JobContext, llm
# from livekit.plugins import noise_cancellation, silero, deepgram, google
# from logging import getLogger
# from livekit.agents import ModelSettings
# from livekit import rtc

# from guards import ContentGuardrail

# logger = getLogger("agents logs")
# load_dotenv(".env")

# class Assistant(Agent):
#     def __init__(self) -> None:
#         super().__init__(
#             instructions="""You are a helpful voice AI assistant.
#             You eagerly assist users with their questions by providing information from your extensive knowledge.
#             Your responses are concise, to the point, and without any complex formatting or punctuation including emojis or symbols.
#             You are curious, friendly, and have a sense of humor."""
#         )

#         # Initialize guardrail
#         self.guardrail = ContentGuardrail()
#     async def tts_node(
#         self,
#         text: AsyncIterable[str],
#         model_settings: ModelSettings,
#     ) -> AsyncIterable[rtc.AudioFrame]:
#         """
#         Pipeline node: Logs agent response text before TTS synthesis.
#         Delegates to default TTS after logging.
#         """
#         # Log text chunks as they arrive
#         async def log_text_chunks() -> AsyncIterable[str]:
#             async for chunk in text:
#                 logger.info(f"🔊 Agent Response: {chunk}")
#                 yield chunk
        
#         # Delegate to default TTS implementation
#         async for frame in Agent.default.tts_node(self, log_text_chunks(), model_settings):
#             yield frame

#     async def before_llm_cb(
#         self, message: llm.ChatMessage
#     ) -> llm.ChatMessage | None:
#         """
#         Called before sending user input to LLM.
#         This is the proper place for guardrail checks.
#         """
#         user_text = message.content
#         logger.info(f"👤 User input: {user_text}")
        
#         # Check guardrails
#         guard_result = self.guardrail.check(user_text)
        
#         if guard_result.is_blocked:
#             logger.warning(f"🚫 BLOCKED - Category: {guard_result.category}")
#             logger.warning(f"🚫 Reason: {guard_result.reason}")
            
#             # Send decline message
#             decline_message = self.guardrail.get_decline_message(guard_result.category)
#             await self.session.say(decline_message, add_to_chat_context=False)
            
#             # Return None to prevent LLM processing
#             return None
        
#         logger.info(f"✅ Content passed guardrail check")
#         # Return the message to continue normal processing
#         return message


    
#     async def on_enter(self) -> None:
#         print("Session started. Sending greeting...")
#         await self.session.say("Hi Nikhil, how can I help you today?")

# async def entrypoint(ctx: JobContext):
#     session = AgentSession(
#         stt=deepgram.STTv2(
#             model="flux-general-en",
#             eager_eot_threshold=0.4,
#         ),
#         llm=google.LLM(
#             model="gemini-2.5-flash",
#         ),
#         tts=deepgram.TTS(
#             model="aura-asteria-en",
#         ),
#         vad=silero.VAD.load()
#     )

#     await session.start(
#         room=ctx.room,
#         agent=Assistant(),
#         room_input_options=RoomInputOptions(
#             noise_cancellation=noise_cancellation.BVC(),
#         ),
#     )


# if __name__ == "__main__":
#     agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))


import logging
from dotenv import load_dotenv
from typing import AsyncIterable
from livekit import RPC

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, JobContext, llm
from livekit.plugins import noise_cancellation, silero, deepgram, google
from logging import getLogger
from livekit.agents import ModelSettings
from livekit import rtc

# Import the guardrail
from guards import ContentGuardrail

logger = getLogger("agents logs")
logger.setLevel(logging.INFO)
load_dotenv(".env")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis or symbols.
            You are curious, friendly, and have a sense of humor."""
        )
        # Initialize guardrail
        self.guardrail = ContentGuardrail()
        self._should_block = False
    
    async def on_user_turn_completed(
        self,
        turn_ctx: llm.ChatContext,
        new_message: llm.ChatMessage,
    ) -> None:
        """
        Called when the user completes their turn, before the message is added to context.
        This is the perfect place for guardrail checks.
        """
        # Extract text content from the message
        user_text = ""
        if isinstance(new_message.content, str):
            user_text = new_message.content
        elif isinstance(new_message.content, list):
            for item in new_message.content:
                if isinstance(item, str):
                    user_text += item
        
        logger.info(f"👤 User input: {user_text}")
        
        # Check guardrails
        guard_result = self.guardrail.check(user_text)
        
        if guard_result.is_blocked:
            logger.warning(f"🚫 BLOCKED - Category: {guard_result.category}")
            logger.warning(f"🚫 Reason: {guard_result.reason}")
            
            # Set flag to block LLM response
            self._should_block = True
            
            # Send decline message (correct parameter name)
            decline_message = self.guardrail.get_decline_message(guard_result.category)
            await self.session.say(decline_message, add_to_chat_ctx=False)
            
            # Modify the message to prevent it from being processed
            new_message.content = "[BLOCKED BY GUARDRAIL]"
        else:
            logger.info(f"✅ Content passed guardrail check")
            self._should_block = False
    
    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tool_ctx: llm.ToolContext,
        model_settings: ModelSettings,
    ) -> AsyncIterable[llm.ChatChunk | str] | None:
        """
        Override LLM node to skip processing if content was blocked.
        """
        # If the content was blocked, return None to skip LLM processing
        if self._should_block:
            logger.info("⏭️  Skipping LLM processing due to guardrail block")
            self._should_block = False  # Reset flag
            return None
        
        # Otherwise, proceed with normal LLM processing
        return Agent.default.llm_node(self, chat_ctx, tool_ctx, model_settings)
    
    async def tts_node(
        self,
        text: AsyncIterable[str],
        model_settings: ModelSettings,
    ) -> AsyncIterable[rtc.AudioFrame]:
        """
        Pipeline node: Logs agent response text before TTS synthesis.
        """
        async def log_text_chunks() -> AsyncIterable[str]:
            async for chunk in text:
                logger.info(f"🔊 Agent Response: {chunk}")
                yield chunk
        
        async for frame in Agent.default.tts_node(self, log_text_chunks(), model_settings):
            yield frame
    
    async def on_enter(self) -> None:
        logger.info("Session started. Sending greeting...")
        await self.session.say("Hi Nikhil, how can I help you today?")

    @room.local_participant.register_rpc_method("greet")
    async def handle_greet(data: RpcInvocationData):
        print(f"Received greeting from {data.caller_identity}: {data.payload}")
        return f"Hello, {data.caller_identity}!"

    


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
