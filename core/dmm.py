import json
import httpx
from groq import Groq
from core.config import Config


class DecisionMakingModule:
    def __init__(self):
        self.groq_client = None

        if Config.GROQ_API_KEY and not Config.FORCE_OFFLINE:
            try:
                self.groq_client = Groq(api_key=Config.GROQ_API_KEY)
            except Exception:
                pass

        self.ollama_url = Config.OLLAMA_BASE_URL
        self.ollama_model = Config.OLLAMA_DEFAULT_MODEL

    # ================================================================
    # RULE-BASED PREFILTER (VERY IMPORTANT)
    # ================================================================
    def _rule_based_classification(self, prompt: str):
        text = prompt.lower().strip()

        # Greetings → always chat
        if text in ["hi", "hii", "hello", "hey"]:
            return {"type": "chat", "argument": "", "value": None}

        # If user asks to write/build/code → chat
        if any(word in text for word in ["write", "build", "create", "make", "program", "code"]):
            return {"type": "chat", "argument": "", "value": None}

        # If sentence length > 3 words → usually chat
        if len(text.split()) > 3:
            return {"type": "chat", "argument": "", "value": None}

        # Explicit search trigger
        if text.startswith("search ") or text.startswith("google "):
            return {
                "type": "search",
                "argument": text.replace("search", "").replace("google", "").strip(),
                "value": None,
            }

        # Weather trigger
        if "weather" in text:
            return {
                "type": "weather",
                "argument": text.replace("weather", "").strip(),
                "value": None,
            }

        # Media control explicit commands
        media_keywords = ["volume", "mute", "play", "pause", "next", "previous"]
        if any(word in text for word in media_keywords):
            return {"type": "media", "argument": text, "value": None}

        return None  # Let LLM decide

    # ================================================================
    # MAIN ROUTER
    # ================================================================
    def route_intent(self, prompt: str, is_online: bool) -> dict:

        prompt_clean = prompt.strip()

        # 1️⃣ RULE-BASED FIRST
        rule_result = self._rule_based_classification(prompt_clean)
        if rule_result:
            return rule_result

        # 2️⃣ FALLBACK TO LLM ROUTING (LOW CONFIDENCE MODEL SAFE)
        system_directive = (
            "You are a strict intent router.\n"
            "Return ONLY JSON with keys: type, argument, value.\n"
            "Allowed types: weather, search, media, open_app, chat.\n"
            "Default to chat unless user clearly asks to open app, search web, or control media.\n"
            "If unsure → chat.\n"
        )

        default = {"type": "chat", "argument": "", "value": None}

        # --- CLOUD ROUTING ---
        if is_online and self.groq_client:
            try:
                completion = self.groq_client.chat.completions.create(
                    model=Config.GROQ_FAST_MODEL,
                    messages=[
                        {"role": "system", "content": system_directive},
                        {"role": "user", "content": prompt_clean},
                    ],
                    temperature=0.0,
                )

                result = json.loads(completion.choices[0].message.content)
                return self._validate(result)

            except Exception:
                return default

        # --- LOCAL OLLAMA ROUTING ---
        try:
            payload = {
                "model": self.ollama_model,
                "messages": [
                    {"role": "system", "content": system_directive},
                    {"role": "user", "content": prompt_clean},
                ],
                "stream": False,
                "options": {"temperature": 0.0},
            }

            response = httpx.post(
                self.ollama_url,
                json=payload,
                timeout=10.0,
            )

            if response.status_code == 200:
                content = response.json().get("message", {}).get("content", "")
                result = json.loads(content)
                return self._validate(result)

        except Exception:
            pass

        return default

    # ================================================================
    # SAFETY VALIDATION
    # ================================================================
    def _validate(self, data: dict):
        if not isinstance(data, dict):
            return {"type": "chat", "argument": "", "value": None}

        allowed = {"weather", "search", "media", "open_app", "chat"}
        if data.get("type") not in allowed:
            return {"type": "chat", "argument": "", "value": None}

        return {
            "type": data.get("type"),
            "argument": str(data.get("argument", "")).strip(),
            "value": data.get("value"),
        }