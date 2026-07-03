import sys
import asyncio
import keyboard
import urllib.request
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QTimer
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QLabel, QPushButton, QCheckBox, QFileDialog
)

from core.config import Config
from interface.styles import Styles
from core.engine import DiabloEngine
from core.parser import markdown_to_html
from core.sandbox import SystemSandbox
from services.file_manager import FileManager


# =====================================================================
# SHARED ENGINE SINGLETON
# Prevents a new DiabloEngine (+ Groq client + SessionMemory) being
# constructed on every single message send.
# =====================================================================
_shared_engine: DiabloEngine | None = None

def get_shared_engine() -> DiabloEngine:
    global _shared_engine
    if _shared_engine is None:
        _shared_engine = DiabloEngine()
    return _shared_engine


# =====================================================================
# NETWORK MONITOR THREAD
# =====================================================================
class NetworkMonitor(QThread):
    status_changed = pyqtSignal(bool)

    def __init__(self, check_interval_ms: int = 2000):
        super().__init__()
        self.check_interval = check_interval_ms
        self.was_online = None
        self.running = True

    def run(self):
        while self.running:
            current_status = self._check_connectivity()
            if current_status != self.was_online:
                self.was_online = current_status
                self.status_changed.emit(current_status)
            self.msleep(self.check_interval)

    def _check_connectivity(self) -> bool:
        """
        Uses a raw TCP socket to 8.8.8.8:53 (Google DNS).
        Much faster and lighter than a full HTTP request — never hangs.
        """
        try:
            import socket
            sock = socket.create_connection(("8.8.8.8", 53), timeout=1.5)
            sock.close()
            return True
        except OSError:
            return False

    def stop(self):
        self.running = False


# =====================================================================
# KEYBOARD HOTKEY WORKER
# =====================================================================
class KeyboardWorker(QObject):
    toggle_signal = pyqtSignal()
    shutdown_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._hooked = False

    def start_listening(self):
        keyboard.add_hotkey(Config.HOTKEY_REVEAL, self.trigger_toggle)
        keyboard.add_hotkey(Config.HOTKEY_TERMINATE, self.trigger_shutdown)
        self._hooked = True

    def trigger_toggle(self):
        self.toggle_signal.emit()

    def trigger_shutdown(self):
        self.shutdown_signal.emit()

    def stop(self):
        """Unhooks all keyboard listeners cleanly before thread shutdown."""
        if self._hooked:
            try:
                keyboard.unhook_all()
                self._hooked = False
                print("[KeyboardWorker]: Hotkeys unhooked cleanly.")
            except Exception as e:
                print(f"[KeyboardWorker WARNING]: Unhook failed -> {e}")


# =====================================================================
# STREAMING WORKER THREAD
# =====================================================================
class StreamingWorker(QThread):
    token_received = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(
        self,
        prompt: str,
        is_online: bool,
        vision_b64=None,
        file_context=None,
    ):
        super().__init__()
        self.prompt = prompt
        self.is_online = is_online
        self.vision_b64 = vision_b64
        self.file_context = file_context
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        try:
            asyncio.run(self._fetch_stream())
        except Exception as e:
            self.token_received.emit(f"\n[💥 Thread Loop Exception: {str(e)}]\n")
        finally:
            self.finished.emit()

    async def _fetch_stream(self):
        # Use the shared singleton engine — no reconstruction overhead
        engine = get_shared_engine()
        async for token in engine.generate_stream(
            self.prompt,
            self.is_online,
            is_running_callback=lambda: self._is_running,
            vision_b64=self.vision_b64,
            file_context=self.file_context,
        ):
            if not self._is_running:
                break
            self.token_received.emit(token)
        # NOTE: Do NOT call engine.close() here — it's a shared singleton.
        # Cleanup happens in DiabloHUD.shutdown_application().


# =====================================================================
# MAIN HUD WINDOW
# =====================================================================
class DiabloHUD(QWidget):
    def __init__(self):
        super().__init__()
        self.is_online_state = False
        self.active_streamer: StreamingWorker | None = None
        self.full_conversation_history = ""
        self.pending_file_context = ""
        self._render_pending = False   # Throttle flag for HTML re-render
        self.init_ui()
        self.start_network_sentinel()

    # ------------------------------------------------------------------
    # UI CONSTRUCTION
    # ------------------------------------------------------------------
    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(720, 460)
        self.center_on_screen()

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.container = QWidget(self)
        self.container.setObjectName("ContainerFrame")
        self.container.setStyleSheet(Styles.get_frame_style(is_online=False))

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(12)

        # --- Telemetry Header ---
        telemetry_layout = QHBoxLayout()
        self.telemetry_engine = QLabel("SYS: INITIALIZING INFRASTRUCTURE CORES...")
        self.telemetry_engine.setStyleSheet(
            "color: #aaaaaa; font-family: 'Consolas', monospace; font-size: 11px; font-weight: bold;"
        )
        self.telemetry_ping = QLabel("PING: -- ms")
        self.telemetry_ping.setStyleSheet(
            "color: #666666; font-family: 'Consolas', monospace; font-size: 11px;"
        )
        self.voice_toggle = QCheckBox("VOICE INGEST CONTROL")
        self.voice_toggle.setStyleSheet(Styles.VOICE_CHECKBOX)
        self.voice_toggle.setToolTip("Voice input (not yet implemented)")
        self.voice_toggle.setEnabled(False)   # Honest: disable until implemented

        telemetry_layout.addWidget(self.telemetry_engine)
        telemetry_layout.addWidget(self.telemetry_ping)
        telemetry_layout.addStretch()
        telemetry_layout.addWidget(self.voice_toggle)
        container_layout.addLayout(telemetry_layout)

        # --- Input Row ---
        input_layout = QHBoxLayout()

        self.btn_attach = QPushButton("📎")
        self.btn_attach.setToolTip("Attach File Content to Context")
        self.btn_attach.setStyleSheet(Styles.UTILITY_BUTTON + "font-size: 14px; padding: 6px 10px;")
        self.btn_attach.clicked.connect(self.trigger_file_explorer_dialog)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(
            " Ask Diablo, execute commands ( >dir ), evaluate scripts ( >>print(5) )..."
        )
        self.input_field.setStyleSheet(Styles.INPUT_FIELD)

        self.btn_halt = QPushButton("🛑 HALT")
        self.btn_halt.setStyleSheet(Styles.HALT_BUTTON)
        self.btn_halt.setVisible(False)
        self.btn_halt.clicked.connect(self.trigger_halt)

        input_layout.addWidget(self.btn_attach)
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.btn_halt)
        container_layout.addLayout(input_layout)

        # --- Output Canvas ---
        self.output_view = QTextEdit()
        self.output_view.setReadOnly(True)
        self.output_view.setPlaceholderText(
            "System Active. Use Alt+D to show/hide the HUD layout pane..."
        )
        self.output_view.setStyleSheet(Styles.OUTPUT_VIEW)
        container_layout.addWidget(self.output_view)

        # --- Footer Utilities ---
        utilities_layout = QHBoxLayout()
        self.btn_copy_code = QPushButton("COPY CONSOLE")
        self.btn_export_notepad = QPushButton("OPEN IN NOTEPAD")
        self.btn_copy_code.setStyleSheet(Styles.UTILITY_BUTTON)
        self.btn_export_notepad.setStyleSheet(Styles.UTILITY_BUTTON)
        self.btn_copy_code.clicked.connect(self.extract_and_copy_code)
        self.btn_export_notepad.clicked.connect(self.export_to_local_notepad)

        self.footer_hint = QLabel("Esc to Sleep · Win+Esc to Shutdown")
        self.footer_hint.setStyleSheet(
            "color: #555555; font-size: 11px; font-family: 'Segoe UI', sans-serif;"
        )

        utilities_layout.addWidget(self.btn_copy_code)
        utilities_layout.addWidget(self.btn_export_notepad)
        utilities_layout.addStretch()
        utilities_layout.addWidget(self.footer_hint)
        container_layout.addLayout(utilities_layout)

        main_layout.addWidget(self.container)
        self.setLayout(main_layout)
        self.input_field.returnPressed.connect(self.handle_input_submission)

        # Render throttle timer — batches rapid token renders into ~60ms intervals
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(60)
        self._render_timer.timeout.connect(self._flush_render)

    # ------------------------------------------------------------------
    # NETWORK SENTINEL
    # ------------------------------------------------------------------
    def start_network_sentinel(self):
        self.network_thread = NetworkMonitor(check_interval_ms=1500)
        self.network_thread.status_changed.connect(self.handle_network_mutation)
        self.network_thread.start()

    def handle_network_mutation(self, is_online: bool):
        self.is_online_state = is_online
        self.container.setStyleSheet(Styles.get_frame_style(is_online))
        if is_online:
            self.telemetry_engine.setText(
                f"SYS: [ONLINE // GROQ LPU] -> {Config.GROQ_FAST_MODEL}"
            )
            self.telemetry_engine.setStyleSheet(
                "color: #ff4d4d; font-family: 'Consolas', monospace; font-size: 11px; font-weight: bold;"
            )
            self.telemetry_ping.setText("PING: CLOUD READY")
        else:
            self.telemetry_engine.setText(
                f"SYS: [LOCAL ENGINE // EDGE OLLAMA] -> {Config.OLLAMA_DEFAULT_MODEL}"
            )
            self.telemetry_engine.setStyleSheet(
                "color: #4da6ff; font-family: 'Consolas', monospace; font-size: 11px; font-weight: bold;"
            )
            self.telemetry_ping.setText("PING: LOCAL ENGINE DISCONNECT")

    # ------------------------------------------------------------------
    # FILE ATTACH
    # ------------------------------------------------------------------
    def trigger_file_explorer_dialog(self):
        """Launches native OS file dialog to extract code or document blocks."""
        file_filter = (
            "All Supported Files (*.txt *.py *.pdf *.json *.js *.html *.css *.cpp *.h *.cs)"
            ";;All Files (*.*)"
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Codebase Asset File to Mount", "", file_filter
        )
        if not file_path:
            return

        file_block = FileManager.read_local_file(file_path)

        if file_block.startswith("["):
            self.input_field.setPlaceholderText(f" {file_block}")
        else:
            import os
            filename = os.path.basename(file_path)
            self.pending_file_context = file_block
            self.input_field.setPlaceholderText(
                f" 🟢 Mounted File Attachment: '{filename}' successfully cached!"
            )
            self.btn_attach.setText("📎✅")

    # ------------------------------------------------------------------
    # UTILITY BUTTONS
    # ------------------------------------------------------------------
    def extract_and_copy_code(self):
        text = self.output_view.toPlainText().strip()
        if not text:
            return
        QApplication.clipboard().setText(text)
        self.input_field.setPlaceholderText(
            " System text successfully copied to clipboard cache memory!"
        )
        # Use QTimer instead of QThread.msleep — never freeze the main thread
        QTimer.singleShot(
            1500,
            lambda: self.input_field.setPlaceholderText(
                " Ask Diablo, execute commands ( >dir ), evaluate scripts ( >>print(5) )..."
            ),
        )

    def export_to_local_notepad(self):
        text = self.output_view.toPlainText().strip()
        if text:
            SystemSandbox.spawn_notepad_with_content(text)

    def trigger_halt(self):
        if self.active_streamer and self.active_streamer.isRunning():
            self.active_streamer.stop()
            self.btn_halt.setVisible(False)
            self.btn_halt.setEnabled(True)   # pre-reset for next use
            self.input_field.setDisabled(False)
            self.input_field.setFocus()

    # ------------------------------------------------------------------
    # WINDOW MANAGEMENT
    # ------------------------------------------------------------------
    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def toggle_window(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
            self.input_field.setFocus()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # INPUT HANDLING
    # ------------------------------------------------------------------
    def handle_input_submission(self):
        text = self.input_field.text().strip()

        # Guard: need either text OR a mounted file to do anything
        has_vision_trigger = text.startswith("/see")
        has_content = bool(text) or bool(self.pending_file_context)
        if not has_content and not has_vision_trigger:
            return

        vision_b64_payload = None

        # =====================================================================
        # ROUTE A: VISION (/see)
        # =====================================================================
        if has_vision_trigger:
            self.input_field.clear()          # clear immediately for UX
            self.hide()
            QApplication.processEvents()
            QThread.msleep(300)

            from services.vision import VisionSentinel
            vision_b64_payload = VisionSentinel.capture_primary_desktop()

            self.show()
            self.raise_()
            self.activateWindow()
            self.input_field.setFocus()

            prompt_cleaned = text.replace("/see", "", 1).strip()
            if not prompt_cleaned:
                prompt_cleaned = (
                    "Analyze this development workspace view screen space for issues or optimization logs."
                )

            self.full_conversation_history += (
                f"\n\n**You 👤 [VISION SNAPSHOT]:** *{prompt_cleaned}*\n\n**Diablo 🌌:** "
            )
            text = prompt_cleaned

        # =====================================================================
        # ROUTE B: PYTHON REPL (>>)
        # =====================================================================
        elif text.startswith(">>"):
            python_payload = text[2:].strip()
            self.full_conversation_history += (
                f"\n\n**You 👤 [EXEC PYTHON]:** `>> {python_payload}`\n\n**Console Output 💻:**\n"
            )
            self.input_field.clear()
            output = SystemSandbox.execute_double_arrow_python(python_payload)
            self.full_conversation_history += f"```plaintext\n{output}\n```"
            self._flush_render()
            return

        # =====================================================================
        # ROUTE C: SHELL (>)
        # =====================================================================
        elif text.startswith(">"):
            shell_payload = text[1:].strip()
            self.full_conversation_history += (
                f"\n\n**You 👤 [EXEC TERMINAL]:** `> {shell_payload}`\n\n**Console Output 💻:**\n"
            )
            self.input_field.clear()
            output = SystemSandbox.execute_single_arrow_shell(shell_payload)
            self.full_conversation_history += f"```plaintext\n{output}\n```"
            self._flush_render()
            return

        # =====================================================================
        # ROUTE D: STANDARD CHAT / FILE CONTEXT
        # =====================================================================
        file_payload = None
        if self.pending_file_context:
            file_payload = self.pending_file_context
            self.pending_file_context = ""
            self.btn_attach.setText("📎")
            self.full_conversation_history += (
                f"\n\n**You 👤 [FILE ATTACHED]:** *Context loaded safely.*\n"
                f"**You 👤:** {text}\n\n**Diablo 🌌:** "
            )
        else:
            self.full_conversation_history += (
                f"\n\n**You 👤:** {text}\n\n**Diablo 🌌:** "
            )

        self.input_field.clear()
        self.input_field.setPlaceholderText(
            " Ask Diablo, execute commands ( >dir ), evaluate scripts ( >>print(5) )..."
        )
        self.input_field.setDisabled(True)
        self.btn_halt.setVisible(True)

        self.active_streamer = StreamingWorker(
            text,
            self.is_online_state,
            vision_b64=vision_b64_payload,
            file_context=file_payload,
        )
        self.active_streamer.token_received.connect(self.append_stream_token)
        self.active_streamer.finished.connect(self.reset_input_state)
        self.active_streamer.start()

    # ------------------------------------------------------------------
    # STREAMING RENDER (THROTTLED)
    # ------------------------------------------------------------------
    def append_stream_token(self, token: str):
        """
        Accumulates tokens and triggers a batched re-render via QTimer.
        This prevents calling setHtml() 2000+ times for a long response
        and eliminates visible UI stutter during streaming.
        """
        self.full_conversation_history += token
        if not self._render_pending:
            self._render_pending = True
            self._render_timer.start()

    def _flush_render(self):
        """Actually performs the HTML render — called by timer or directly for sync routes."""
        self._render_pending = False
        self.output_view.setHtml(markdown_to_html(self.full_conversation_history))
        cursor = self.output_view.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.output_view.setTextCursor(cursor)

    def reset_input_state(self):
        self._flush_render()          # ensure final render happens after stream ends
        self.input_field.setDisabled(False)
        self.btn_halt.setVisible(False)
        self.btn_halt.setEnabled(True)
        self.input_field.setFocus()

    # ------------------------------------------------------------------
    # SHUTDOWN
    # ------------------------------------------------------------------
    def shutdown_application(self):
        print("\n[!] Safely dismantling engine monitors and releasing keyboard anchors...")
        try:
            self.network_thread.stop()
            self.network_thread.wait(2000)
        except Exception as e:
            print(f"[Shutdown WARNING]: Network thread -> {e}")

        try:
            if self.active_streamer and self.active_streamer.isRunning():
                self.active_streamer.stop()
                self.active_streamer.wait(2000)
        except Exception as e:
            print(f"[Shutdown WARNING]: Stream worker -> {e}")

        try:
            keyboard.unhook_all()
        except Exception as e:
            print(f"[Shutdown WARNING]: Keyboard unhook -> {e}")

        try:
            import asyncio
            engine = get_shared_engine()
            loop = asyncio.new_event_loop()
            loop.run_until_complete(engine.close())
            loop.close()
        except Exception as e:
            print(f"[Shutdown WARNING]: Engine close -> {e}")

        QApplication.quit()


# =====================================================================
# STANDALONE LAUNCH
# =====================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    hud = DiabloHUD()
    hud.show()
    sys.exit(app.exec())