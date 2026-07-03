import os
import json
import asyncio
import getpass
import httpx
from datetime import datetime
from groq import AsyncGroq
from core.config import Config
from core.memory import SessionMemory
from core.dmm import DecisionMakingModule


class DiabloEngine:
    def __init__(self):
        self.groq_client = None

        if Config.GROQ_API_KEY and not Config.FORCE_OFFLINE:
            try:
                self.groq_client = AsyncGroq(api_key=Config.GROQ_API_KEY)
                print("[DIABLO CORE]: Groq cloud engine initialized.")
            except Exception as e:
                print(f"[DIABLO CORE]: Groq binding failed: {str(e)}")

        self.ollama_url = Config.OLLAMA_BASE_URL
        self.ollama_model = Config.OLLAMA_DEFAULT_MODEL

        self.vault = SessionMemory()
        self.dmm = DecisionMakingModule()

    @staticmethod
    def _resolve_username() -> str:
        try:
            return getpass.getuser()
        except Exception:
            return "operator"

    async def generate_stream(
        self,
        prompt: str,
        is_online: bool,
        is_running_callback=None,
        vision_b64=None,
        file_context=None,
    ):
        if is_running_callback is None:
            is_running_callback = lambda: True

        prompt_clean = prompt.strip()
        prompt_lower = prompt_clean.lower()

        response_saved = False
        full_assistant_generation = ""

        # ================================================================
        # CLEAR MEMORY COMMAND
        # ================================================================
        if prompt_lower == "/clear":
            self.vault.wipe_memory_vault()
            yield "\n[🧠 Memory cleared successfully.]\n"
            return

        # ================================================================
        # DMM INTENT ROUTING (Skip if file/image attached)
        # ================================================================
        if not vision_b64 and not file_context:
            routing_decision = self.dmm.route_intent(prompt_clean, is_online)

            if isinstance(routing_decision, dict):
                task_type = routing_decision.get("type", "chat")
                argument = str(routing_decision.get("argument", "")).strip()
                value = routing_decision.get("value")

                # Weather
                if task_type == "weather":
                    from services.live_tools import LiveTools
                    location = argument or "Delhi"
                    yield f"[Weather Lookup: {location}]\n\n"
                    yield LiveTools.get_current_weather(location)
                    return

                # Search
                if task_type == "search":
                    from services.live_tools import LiveTools
                    query = argument or prompt_clean
                    LiveTools.live_web_search(query)
                    yield f"[Search opened in browser: {query}]"
                    return

                # Media
                if task_type == "media":
                    from services.system_tools import SystemTools
                    yield SystemTools.execute_media_command(argument, value)
                    return

                # Open App
                if task_type == "open_app":
                    from services.system_tools import SystemTools
                    yield SystemTools.open_application(argument)
                    return

        # ================================================================
        # SYSTEM PROMPT BUILD
        # ================================================================
        current_user = self._resolve_username()
        current_workspace = os.getcwd()

        system_prompt = (
            f"You are Diablo, a powerful desktop assistant. "
            f"User: {current_user}. Workspace: {current_workspace}. "
            "Be direct, precise, efficient. Avoid unnecessary fluff."
        )

        if file_context:
            system_prompt += (
                f"\n\n[ATTACHED FILE CONTEXT - USE ONLY FOR THIS RESPONSE]:\n{file_context}"
            )

        self.vault.append_chat_node(
            "user", prompt_clean if prompt_clean else "[image attached]"
        )

        messages = self.vault.compile_context_array(system_prompt)

        # ================================================================
        # VISION ROUTE (Cloud Only)
        # ================================================================
        if vision_b64:
            if not self.groq_client:
                yield "\n[Vision requires cloud model — not available in offline mode.]\n"
                return

            vision_messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_clean or "Analyze screenshot."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{vision_b64}"
                            },
                        },
                    ],
                },
            ]

            try:
                stream = await self.groq_client.chat.completions.create(
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    messages=vision_messages,
                    stream=True,
                    temperature=0.2,
                )

                async for chunk in stream:
                    if not is_running_callback():
                        break
                    if chunk.choices and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        full_assistant_generation += token
                        yield token

                if full_assistant_generation.strip():
                    self.vault.append_chat_node("assistant", full_assistant_generation)
                return

            except Exception as e:
                yield f"\n[Vision cloud error]: {str(e)}\n"
                return

        # ================================================================
        # HYBRID CLOUD + LOCAL ROUTING
        # ================================================================
        use_cloud = (
            is_online
            and self.groq_client is not None
            and not Config.FORCE_OFFLINE
        )

        if use_cloud:
            try:
                stream = await self.groq_client.chat.completions.create(
                    model=Config.GROQ_FAST_MODEL,
                    messages=messages,
                    stream=True,
                    temperature=0.3,
                )

                async for chunk in stream:
                    if not is_running_callback():
                        break
                    if chunk.choices and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        full_assistant_generation += token
                        yield token

            except Exception as e:
                yield f"\n[Cloud failed — switching to local model...]\n"
                full_assistant_generation = ""
                async for token in self._stream_ollama(messages, is_running_callback):
                    full_assistant_generation += token
                    yield token

        else:
            async for token in self._stream_ollama(messages, is_running_callback):
                full_assistant_generation += token
                yield token

        if full_assistant_generation.strip():
            self.vault.append_chat_node("assistant", full_assistant_generation)

    # ================================================================
    # OLLAMA STREAM
    # ================================================================
    async def _stream_ollama(self, messages, is_running_callback):
        payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.3},
        }

        try:
            timeout = float(Config.REQUEST_TIMEOUT)

            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST", self.ollama_url, json=payload
                ) as response:

                    if response.status_code != 200:
                        yield f"\n[OLLAMA ERROR {response.status_code}]\n"
                        return

                    async for line in response.aiter_lines():
                        if not is_running_callback():
                            break

                        if line:
                            try:
                                data = json.loads(line)
                                token = data.get("message", {}).get("content", "")
                                if token:
                                    yield token
                            except json.JSONDecodeError:
                                continue

        except httpx.ConnectError:
            yield "\n[❌ OLLAMA OFFLINE]: Could not reach local Ollama server.\n"
        except httpx.ReadTimeout:
            yield "\n[❌ OLLAMA TIMEOUT]: Model took too long to respond.\n"
        except Exception as e:
            yield f"\n[❌ OLLAMA FAILURE]: {str(e)}\n"

    # ================================================================
    # CLEANUP
    # ================================================================
    async def close(self):
        if self.groq_client:
            try:
                await self.groq_client.close()
            except Exception:
                pass