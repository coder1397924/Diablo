import os
import sys
import shlex
import subprocess
import tempfile

# Maximum characters returned from any subprocess to prevent GUI memory spikes
_MAX_OUTPUT_CHARS = 20_000

# Interactive-mode flags that would freeze the UI waiting for stdin
_INTERACTIVE_FLAGS = {"-i", "--interactive", "-it", "-ti"}

# Commands that open full interactive REPL sessions when run alone
_INTERACTIVE_COMMANDS = {"python", "python3", "cmd", "powershell", "bash", "sh", "zsh", "fish", "node", "irb", "ipython"}


def _cap_output(text: str, label: str = "") -> str:
    """Truncates oversized output so the GUI never chokes on a massive string."""
    if len(text) <= _MAX_OUTPUT_CHARS:
        return text
    truncated = text[:_MAX_OUTPUT_CHARS]
    marker = f"\n\n... [OUTPUT CAPPED AT {_MAX_OUTPUT_CHARS} CHARS — {label} truncated to protect UI]"
    return truncated + marker


class SystemSandbox:

    # ------------------------------------------------------------------
    # CHANNEL: >> Python Execution
    # ------------------------------------------------------------------
    @staticmethod
    def execute_double_arrow_python(python_code: str) -> str:
        """
        Executes raw Python snippets locally via the >> channel.
        Uses temp file + isolated subprocess — NOT eval/exec for safety.
        """
        python_code = python_code.strip()
        if not python_code:
            return (
                "[Python Sandbox Info]: Provide code statements after '>>'.\n"
                "Example: >>print(5 + 10)"
            )

        temp_path = None
        try:
            # Write code to temp file
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".py",
                mode="w",
                encoding="utf-8"
            ) as temp_script:
                temp_script.write(python_code)
                temp_path = temp_script.name

            process = subprocess.Popen(
                [sys.executable, temp_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                # No shell=True here — safe list form
            )

            timed_out = False
            try:
                stdout, stderr = process.communicate(timeout=8.0)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                timed_out = True

            # Build output from whatever was captured (even on timeout)
            output_parts = []
            if stdout and stdout.strip():
                output_parts.append(_cap_output(stdout.strip(), "stdout"))
            if stderr and stderr.strip():
                output_parts.append(f"[Stderr]:\n{_cap_output(stderr.strip(), 'stderr')}")

            if timed_out:
                partial = "\n\n".join(output_parts)
                timeout_msg = "[⏱ Timeout Limit Exceeded]: Python script terminated after 8s."
                return f"{timeout_msg}\n\n[Partial Output Before Timeout]:\n{partial}" if partial else timeout_msg

            if output_parts:
                return "\n\n".join(output_parts)

            return "[✅ Python script executed successfully with no printed outputs]"

        except Exception as e:
            return f"[Python Sandbox Exception]: {str(e)}"

        finally:
            # ALWAYS clean up temp file — even on timeout or exception
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    # ------------------------------------------------------------------
    # CHANNEL: > Shell Execution
    # ------------------------------------------------------------------
    @staticmethod
    def execute_single_arrow_shell(shell_command: str) -> str:
        """
        Executes a standard terminal command via the > channel.

        Security note: Uses shlex tokenization instead of shell=True to
        mitigate shell injection from chained operators (&, |, &&, ||).
        """
        shell_command = shell_command.strip()
        if not shell_command:
            return "[Sandbox Error]: Empty shell payload detected."

        # ---------------------------------------------------------------
        # Tokenise safely using shlex (handles quoted args correctly)
        # ---------------------------------------------------------------
        try:
            tokens = shlex.split(shell_command)
        except ValueError as e:
            return f"[Sandbox Error]: Failed to parse command -> {e}"

        if not tokens:
            return "[Sandbox Error]: Empty shell payload after parsing."

        first_word = tokens[0].lower()

        # ---------------------------------------------------------------
        # Block interactive REPL sessions — they freeze the UI forever
        # ---------------------------------------------------------------
        if first_word in _INTERACTIVE_COMMANDS:
            # Block if run alone
            if len(tokens) == 1:
                return (
                    f"[Diablo Shell Info]: Interactive session '{first_word}' blocked. "
                    f"Provide explicit arguments (e.g., >{first_word} --version)."
                )
            # Block if interactive flag present
            if any(t in _INTERACTIVE_FLAGS for t in tokens[1:]):
                return (
                    f"[Diablo Shell Info]: Interactive flag detected in '{first_word}' command — blocked to prevent UI freeze."
                )

        # Special case: bare `ollama` → show help instead
        if len(tokens) == 1 and first_word == "ollama":
            tokens = ["ollama", "--help"]

        try:
            process = subprocess.Popen(
                tokens,                        # list form — no shell injection risk
                shell=False,                   # explicit False for clarity
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )

            timed_out = False
            try:
                stdout, stderr = process.communicate(timeout=10.0)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                timed_out = True

            # Combine stdout + stderr (never discard either)
            output_parts = []
            if stdout and stdout.strip():
                output_parts.append(_cap_output(stdout.strip(), "stdout"))
            if stderr and stderr.strip():
                output_parts.append(f"[Stderr Warnings]:\n{_cap_output(stderr.strip(), 'stderr')}")

            if timed_out:
                partial = "\n\n".join(output_parts)
                timeout_msg = "[⏱ Timeout Limit Exceeded]: Process terminated safely after 10s."
                return f"{timeout_msg}\n\n[Partial Output]:\n{partial}" if partial else timeout_msg

            if output_parts:
                return "\n\n".join(output_parts)

            return "[✅ Process exited successfully with no returned data]"

        except FileNotFoundError:
            return f"[Shell Error]: Command '{tokens[0]}' not found. Is it installed and on PATH?"
        except PermissionError:
            return f"[Shell Error]: Permission denied executing '{tokens[0]}'."
        except Exception as e:
            return f"[Shell Exception]: {str(e)}"

    # ------------------------------------------------------------------
    # UTILITY: Open text content in a system editor
    # ------------------------------------------------------------------
    @staticmethod
    def spawn_notepad_with_content(content: str) -> bool:
        """
        Dumps text into a temporary file and opens it in the default system editor.
        Cross-platform: Notepad on Windows, 'open' on macOS, xdg-open on Linux.
        """
        try:
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".txt",
                mode="w",
                encoding="utf-8"
            ) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name

            if sys.platform == "win32":
                subprocess.Popen(["notepad.exe", temp_path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-t", temp_path])
            else:
                # Linux — try common editors in order of preference
                for editor in ["xdg-open", "gedit", "nano", "vi"]:
                    try:
                        subprocess.Popen([editor, temp_path])
                        break
                    except FileNotFoundError:
                        continue
                else:
                    print("[Sandbox Warning]: No suitable editor found on this Linux system.")
                    return False

            return True

        except Exception as e:
            print(f"[Sandbox Error]: Failed to spawn editor -> {e}")
            return False