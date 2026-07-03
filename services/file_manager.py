import os

# =====================================================================
# SECURITY + PERFORMANCE CONSTANTS
# =====================================================================
_MAX_FILE_SIZE_BYTES = 500 * 1024  # 500 KB hard cap
_ALLOWED_BASE_DIR = os.path.abspath(os.getcwd())  # Restrict to current project directory


class FileManager:
    @staticmethod
    def _is_within_allowed_directory(path: str) -> bool:
        """Ensures file access is restricted to project root (prevents system file exfiltration)."""
        try:
            return os.path.commonpath([_ALLOWED_BASE_DIR, path]) == _ALLOWED_BASE_DIR
        except ValueError:
            return False

    @staticmethod
    def _is_binary_file(path: str) -> bool:
        """
        Basic binary detection:
        Reads first 1024 bytes and checks for null byte presence.
        """
        try:
            with open(path, "rb") as f:
                chunk = f.read(1024)
                return b"\x00" in chunk
        except Exception:
            return True

    @staticmethod
    def read_local_file(file_path: str) -> str:
        """
        Safely reads local text assets within workspace framework.
        Enforces:
        - Directory boundary restriction
        - File size ceiling
        - Binary detection
        - Markdown-safe output wrapping
        """
        try:
            target_path = os.path.abspath(os.path.normpath(file_path.strip()))

            if not os.path.exists(target_path):
                return f"[Filesystem Error]: Path not found."

            if os.path.isdir(target_path):
                return "[Filesystem Error]: Targeted path is a directory, not a readable file."

            # Restrict file access to project directory only
            if not FileManager._is_within_allowed_directory(target_path):
                return "[Security Block]: Access denied — file outside permitted workspace scope."

            # Size check (bytes precision)
            file_size = os.path.getsize(target_path)
            if file_size > _MAX_FILE_SIZE_BYTES:
                return (
                    f"[Ceiling Error]: File size ({file_size / 1024:.2f} KB) "
                    f"exceeds the 500KB context protection limit."
                )

            # Binary detection
            if FileManager._is_binary_file(target_path):
                return "[Unsupported File Type]: Binary file detected. Only readable text-based files are supported."

            # Read file safely
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Normalize newlines
            content = content.replace("\r\n", "\n").replace("\r", "\n")

            # Escape triple backticks to prevent markdown breakage
            content = content.replace("```", "`` `")

            # Determine syntax language from extension
            _, ext = os.path.splitext(target_path)
            syntax_lang = ext.replace(".", "").lower() if ext else "plaintext"

            filename = os.path.basename(target_path)

            return (
                f"### TARGET FILE ASSET INGESTED: `{filename}`\n"
                f"```{syntax_lang}\n"
                f"{content}\n"
                f"```"
            )

        except Exception as e:
            return f"[Filesystem Exception]: Could not mount resource: {str(e)}"