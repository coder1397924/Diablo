import sys
import keyboard
import subprocess
import time
import shutil
from typing import Optional


class SystemTools:

    # ================================================================
    # MEDIA CONTROLS
    # ================================================================
    @staticmethod
    def execute_media_command(command: str, amount: Optional[int] = None) -> str:
        """
        Triggers native OS media controls.
        Windows: full support (pycaw + media keys)
        Other OS: partial (media keys only)
        """
        try:
            platform = sys.platform.lower()

            # ----------------------------------------------------------
            # Normalize numeric input safely
            # ----------------------------------------------------------
            if amount is not None:
                try:
                    amount = int(float(amount))
                except Exception:
                    amount = None

            # ----------------------------------------------------------
            # ABSOLUTE VOLUME (Windows Only)
            # ----------------------------------------------------------
            if command == "vol_set" and amount is not None:
                if platform != "win32":
                    return "Absolute volume control supported only on Windows."

                try:
                    from ctypes import POINTER, cast
                    from comtypes import CLSCTX_ALL
                    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(
                        IAudioEndpointVolume._iid_,
                        CLSCTX_ALL,
                        None
                    )
                    volume = cast(interface, POINTER(IAudioEndpointVolume))

                    target_level = max(0, min(100, amount)) / 100.0
                    volume.SetMasterVolumeLevelScalar(target_level, None)
                    return f"System master volume set to {amount}%."

                except Exception as ex:
                    return f"Core Audio API failure: {str(ex)}"

            # ----------------------------------------------------------
            # RELATIVE MEDIA KEYS
            # ----------------------------------------------------------
            if amount is not None and amount > 0:
                presses = max(1, amount // 2)
                change_text = f"{amount}%"
            else:
                presses = 5
                change_text = "10%"

            if command == "vol_up":
                for _ in range(presses):
                    keyboard.send("volume up")
                return f"System volume increased by {change_text}."

            elif command == "vol_down":
                for _ in range(presses):
                    keyboard.send("volume down")
                return f"System volume decreased by {change_text}."

            elif command == "mute":
                keyboard.send("volume mute")
                return "System volume toggled (mute/unmute)."

            elif command == "play_pause":
                keyboard.send("play/pause media")
                return "Media playback toggled."

            elif command == "next":
                keyboard.send("next track")
                return "Skipped to next track."

            elif command == "prev":
                keyboard.send("previous track")
                return "Returned to previous track."

            return f"Unrecognized media command: {command}"

        except Exception as e:
            return f"System media control failed: {str(e)}"

    # ================================================================
    # APPLICATION LAUNCHER
    # ================================================================
    @staticmethod
    def open_application(app_name: str) -> str:
        """
        Attempts to launch an application securely.
        - Uses safe Popen (no shell=True)
        - Windows-specific search macro only used on Windows
        """
        try:
            if not app_name or not app_name.strip():
                return "No application name provided."

            app_clean = app_name.lower().strip()

            # Block suspicious injection characters
            if any(char in app_clean for char in ["&", "|", ";", ">", "<"]):
                return "Unsafe characters detected in application name. Launch aborted."

            platform = sys.platform.lower()

            # ----------------------------------------------------------
            # Direct executable mappings (Windows focused)
            # ----------------------------------------------------------
            direct_mappings = {
                "chrome": "chrome.exe",
                "google chrome": "chrome.exe",
                "notepad": "notepad.exe",
                "calc": "calc.exe",
                "calculator": "calc.exe",
                "cmd": "cmd.exe",
                "terminal": "wt.exe",
                "explorer": "explorer.exe",
                "spotify": "spotify.exe",
                "vs code": "code",
                "vscode": "code"
            }

            target = direct_mappings.get(app_clean, app_clean)

            # ----------------------------------------------------------
            # Strategy A: Direct OS resolution
            # ----------------------------------------------------------
            resolved = shutil.which(target)

            if resolved is not None:
                subprocess.Popen(
                    [resolved],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return f"Application '{app_name}' launched successfully."

            # ----------------------------------------------------------
            # Strategy B: Windows Search Automation Fallback
            # ----------------------------------------------------------
            if platform == "win32":
                try:
                    keyboard.send("windows+s")
                    time.sleep(0.6)
                    keyboard.write(app_clean, delay=0.01)
                    time.sleep(0.4)
                    keyboard.send("enter")
                    return (
                        f"Direct path not found. "
                        f"Triggered Windows Search macro to launch '{app_name}'."
                    )
                except Exception as e:
                    return f"Windows search automation failed: {str(e)}"

            return f"Application '{app_name}' not found on PATH."

        except FileNotFoundError:
            return f"Executable not found: {app_name}"
        except PermissionError:
            return f"Permission denied launching '{app_name}'."
        except Exception as e:
            return f"Application launcher failure: {str(e)}"