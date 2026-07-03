import os


class Config:
    # ================================================================
    # CLOUD CORE ENGINE (GROQ)
    # ================================================================
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
    GROQ_FAST_MODEL = os.environ.get(
        "GROQ_FAST_MODEL",
        "llama-3.3-70b-versatile"
    ).strip()

    # ================================================================
    # LOCAL CORE ENGINE (OLLAMA)
    # ================================================================
    OLLAMA_DEFAULT_MODEL = os.environ.get(
        "OLLAMA_DEFAULT_MODEL",
        "llama3.2:3b"
    ).strip()

    OLLAMA_BASE_URL = os.environ.get(
        "OLLAMA_BASE_URL",
        "http://localhost:11434/api/chat"
    ).strip()

    # ================================================================
    # HOTKEY CONFIGURATION
    # ================================================================
    HOTKEY_REVEAL = os.environ.get("HOTKEY_REVEAL", "alt+d").strip()
    HOTKEY_TERMINATE = os.environ.get("HOTKEY_TERMINATE", "win+esc").strip()

    # ================================================================
    # RUNTIME FLAGS
    # ================================================================
    # If true → never attempt cloud
    FORCE_OFFLINE = os.environ.get(
        "FORCE_OFFLINE",
        "false"
    ).lower() in ("1", "true", "yes")

    # Timeout for Ollama + Groq requests
    REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "60"))

    # ================================================================
    # HELPER METHODS
    # ================================================================
    @classmethod
    def has_cloud_access(cls) -> bool:
        return bool(cls.GROQ_API_KEY) and not cls.FORCE_OFFLINE


# ================================================================
# TESTBENCH
# ================================================================
if __name__ == "__main__":
    print("[CONFIG TEST]")
    print("Cloud Model:", Config.GROQ_FAST_MODEL)
    print("Local Model:", Config.OLLAMA_DEFAULT_MODEL)
    print("Force Offline:", Config.FORCE_OFFLINE)
    print("Timeout:", Config.REQUEST_TIMEOUT)