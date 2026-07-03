import os
import json
import tempfile
import shutil


# Valid roles accepted by LLM APIs
_VALID_ROLES = {"user", "assistant", "system"}

# Hard cap on individual message content length (characters) sent to API
# Prevents single massive file-paste from blowing token limits
_MAX_CONTENT_CHARS = 12_000


def _is_valid_message(entry) -> bool:
    """Returns True only if a history entry is a well-formed LLM message dict."""
    if not isinstance(entry, dict):
        return False
    role = entry.get("role", "")
    content = entry.get("content", "")
    if role not in _VALID_ROLES:
        return False
    if not isinstance(content, str) or not content.strip():
        return False
    return True


class SessionMemory:
    def __init__(self, filename="diablo_history.json", max_history=14):
        """
        Manages rolling conversation thread memory caching.
        Applies a max_history boundary context ceiling to safeguard against API token bloat.

        NOTE: max_history counts individual MESSAGES (not turns).
              1 turn = 1 user message + 1 assistant message = 2 slots.
              Default 14 = 7 full conversation turns retained.
        """
        self.filepath = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            filename
        )
        # Enforce even number so we never have orphaned messages
        self.max_history = max_history if max_history % 2 == 0 else max_history + 1
        self.history: list[dict] = []
        self._load_cache_from_disk()

    # ------------------------------------------------------------------
    # INTERNAL: Disk I/O
    # ------------------------------------------------------------------

    def _load_cache_from_disk(self):
        """Loads previous conversation blocks from local workspace JSON cache."""
        if not os.path.exists(self.filepath):
            return

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                raw = json.load(f)

            # Validate top-level structure
            if not isinstance(raw, list):
                raise ValueError(f"Expected list, got {type(raw).__name__}")

            # Filter out any malformed entries (manual edits, corruption)
            valid = [entry for entry in raw if _is_valid_message(entry)]
            invalid_count = len(raw) - len(valid)
            if invalid_count > 0:
                print(f"[MEMORY CACHE WARNING]: Dropped {invalid_count} malformed history entries.")

            # Ensure history never starts with an assistant message
            while valid and valid[0].get("role") == "assistant":
                valid.pop(0)

            self.history = valid[-self.max_history:]  # enforce window on load too

        except (json.JSONDecodeError, ValueError) as e:
            print(f"[MEMORY CACHE WARNING]: History file corrupt ({e}) -> backing up and resetting.")
            self._backup_corrupt_file()
            self.history = []
        except Exception as e:
            print(f"[MEMORY CACHE WARNING]: Failed to load history -> {e}")
            self.history = []

    def _backup_corrupt_file(self):
        """Renames the corrupt history file instead of destroying it."""
        backup_path = self.filepath + ".corrupt_backup"
        try:
            shutil.copy2(self.filepath, backup_path)
            print(f"[MEMORY CACHE]: Corrupt file backed up to '{backup_path}'.")
        except Exception as e:
            print(f"[MEMORY CACHE WARNING]: Could not back up corrupt file -> {e}")

    def _commit_cache_to_disk(self):
        """
        Atomically writes active conversation memory to disk.
        Uses a temp file + rename strategy to prevent corruption on crash/power loss.
        """
        dir_path = os.path.dirname(self.filepath)
        try:
            # Write to a temp file in the same directory first
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=dir_path,
                delete=False,
                suffix=".tmp"
            ) as tmp_file:
                json.dump(self.history, tmp_file, indent=4, ensure_ascii=False)
                tmp_path = tmp_file.name

            # Atomic rename — on most OS this is an atomic operation
            shutil.move(tmp_path, self.filepath)

        except Exception as e:
            print(f"[MEMORY CACHE ERROR]: Atomic write failure -> {e}")
            # Clean up temp file if it was created
            try:
                if "tmp_path" in dir() and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def append_chat_node(self, role: str, content: str):
        """
        Appends an interaction block and enforces the sliding sequence window.
        Skips empty or whitespace-only content silently.
        """
        if not content or not content.strip():
            return

        # Validate role before appending
        if role not in _VALID_ROLES:
            print(f"[MEMORY CACHE WARNING]: Invalid role '{role}' rejected.")
            return

        self.history.append({"role": role, "content": content.strip()})

        # Enforce rolling history threshold
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

            # Ensure we don't start mid-conversation with an assistant message
            while self.history and self.history[0].get("role") == "assistant":
                self.history.pop(0)

        self._commit_cache_to_disk()

    def compile_context_array(self, system_directive: str) -> list:
        """
        Injects core system parameters in front of cached conversational memory.
        Truncates individual message content to _MAX_CONTENT_CHARS to prevent
        token limit overflows from large file pastes or verbose responses.
        """
        messages = [{"role": "system", "content": system_directive}]

        for entry in self.history:
            content = entry.get("content", "")
            # Truncate oversized messages with a clear marker
            if len(content) > _MAX_CONTENT_CHARS:
                content = content[:_MAX_CONTENT_CHARS] + "\n... [TRUNCATED — content exceeded context window limit]"
            messages.append({"role": entry["role"], "content": content})

        return messages

    def wipe_memory_vault(self):
        """Completely clears localised conversational states and history blocks."""
        self.history = []
        if os.path.exists(self.filepath):
            try:
                os.remove(self.filepath)
                print("[MEMORY CACHE]: Vault wiped. History file removed.")
            except OSError as e:
                print(f"[MEMORY CACHE WARNING]: Could not delete history file -> {e}")
                # File still exists — overwrite with empty array as fallback
                try:
                    with open(self.filepath, "w", encoding="utf-8") as f:
                        json.dump([], f)
                    print("[MEMORY CACHE]: History file overwritten with empty vault instead.")
                except Exception as e2:
                    print(f"[MEMORY CACHE ERROR]: Could not overwrite history file -> {e2}")

    def get_history_snapshot(self) -> list[dict]:
        """Returns a shallow copy of current in-memory history (safe for inspection)."""
        return list(self.history)

    def get_turn_count(self) -> int:
        """Returns the number of complete conversation turns (user+assistant pairs)."""
        return sum(1 for entry in self.history if entry.get("role") == "user")