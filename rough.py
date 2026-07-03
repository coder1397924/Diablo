"""
DIABLO OLLAMA DIAGNOSTIC TOOL
Run this file directly to test if your local Ollama setup is ready.

Usage:
    python rough.py
"""

import sys
import httpx
import json

# Add project root to path so we can import Config
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import Config


def check_ollama_server():
    """Step 1: Is the Ollama server reachable?"""
    print("\n" + "=" * 60)
    print("STEP 1: Checking if Ollama server is running...")
    print("=" * 60)

    base_url = Config.OLLAMA_BASE_URL.replace("/api/chat", "")
    tags_url = f"{base_url}/api/tags"

    try:
        response = httpx.get(tags_url, timeout=5.0)
        if response.status_code == 200:
            print(f"✅ Ollama server is RUNNING at {base_url}")
            return response.json()
        else:
            print(f"❌ Server responded with HTTP {response.status_code}")
            return None
    except httpx.ConnectError:
        print(f"❌ CANNOT CONNECT to {base_url}")
        print("\n🔧 FIX:")
        print("   1. Open a new terminal")
        print("   2. Run: ollama serve")
        print("   3. Keep that terminal open")
        print("   4. Try again")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def check_model_available(tags_data):
    """Step 2: Is the configured model actually pulled?"""
    print("\n" + "=" * 60)
    print("STEP 2: Checking if configured model is downloaded...")
    print("=" * 60)

    target_model = Config.OLLAMA_DEFAULT_MODEL
    models = tags_data.get("models", [])
    model_names = [m.get("name", "") for m in models]

    print(f"🎯 Target model: {target_model}")
    print(f"📦 Available models: {model_names if model_names else 'NONE'}")

    if target_model in model_names:
        print(f"✅ Model '{target_model}' is installed.")
        return True

    # Check if base name matches (e.g. llama3.2:3b vs llama3.2:latest)
    base_name = target_model.split(":")[0]
    matching = [n for n in model_names if n.startswith(base_name)]

    if matching:
        print(f"⚠️  Model '{target_model}' NOT found, but similar ones exist: {matching}")
        print(f"\n🔧 FIX: Update your .env file:")
        print(f"   OLLAMA_DEFAULT_MODEL={matching[0]}")
    else:
        print(f"❌ Model '{target_model}' is NOT installed.")
        print(f"\n🔧 FIX: Download the model by running:")
        print(f"   ollama pull {target_model}")

    return False


def test_chat_completion():
    """Step 3: Actually test a chat completion."""
    print("\n" + "=" * 60)
    print("STEP 3: Testing chat completion...")
    print("=" * 60)

    payload = {
        "model": Config.OLLAMA_DEFAULT_MODEL,
        "messages": [{"role": "user", "content": "Say 'hello' in one word."}],
        "stream": False,
    }

    try:
        response = httpx.post(
            Config.OLLAMA_BASE_URL,
            json=payload,
            timeout=60.0,
        )
        if response.status_code == 200:
            data = response.json()
            reply = data.get("message", {}).get("content", "")
            print(f"✅ Chat works! Model replied: {reply!r}")
            return True
        else:
            print(f"❌ Chat failed with HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except httpx.ReadTimeout:
        print("❌ Chat request timed out (model may be loading — try again).")
        return False
    except Exception as e:
        print(f"❌ Chat request failed: {e}")
        return False


def main():
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║        DIABLO OFFLINE MODE DIAGNOSTIC TOOL                 ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n📋 Configuration:")
    print(f"   OLLAMA_BASE_URL      = {Config.OLLAMA_BASE_URL}")
    print(f"   OLLAMA_DEFAULT_MODEL = {Config.OLLAMA_DEFAULT_MODEL}")

    tags_data = check_ollama_server()
    if not tags_data:
        print("\n❌ DIAGNOSTIC FAILED at Step 1. Fix above and re-run.")
        return

    if not check_model_available(tags_data):
        print("\n❌ DIAGNOSTIC FAILED at Step 2. Fix above and re-run.")
        return

    if not test_chat_completion():
        print("\n❌ DIAGNOSTIC FAILED at Step 3.")
        return

    print("\n" + "=" * 60)
    print("🎉 ALL CHECKS PASSED — Diablo offline mode should work!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()