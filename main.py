import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread

# =====================================================================
# SYSTEM PATH ANCHORING
# =====================================================================
# Hard-inject root project bounds to eradicate internal module routing loops
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# =====================================================================
# SECRET VARIABLE ENVIRONMENT MATRIX INJECTION
# =====================================================================
def load_env_file():
    """Maps secret configurations into system memory space before code imports resolve."""
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if " #" in line:
                    line = line.split(" #", 1)[0].strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
        print("[DIABLO INITIALIZATION]: System credentials loaded into memory space.")
    else:
        print("[DIABLO WARNING]: No active configuration .env matrix detected.")

# Execute pre-flight secret mapping loop IMMEDIATELY
load_env_file()

# NOW it is safe to import internal modules because variables are active
from interface.gui import DiabloHUD, KeyboardWorker

def initialize_diablo_system():
    print("[DIABLO CORE]: Igniting master graphics and hotkey threads...")
    
    app = QApplication(sys.argv)
    hud = DiabloHUD()
    
    # Spin up an independent background process framework to catch key mutations safely
    keyboard_thread = QThread()
    worker = KeyboardWorker()
    worker.moveToThread(keyboard_thread)
    
    keyboard_thread.started.connect(worker.start_listening)
    worker.toggle_signal.connect(hud.toggle_window)
    worker.shutdown_signal.connect(hud.shutdown_application)
    
    # Plug memory teardown leaks by explicitly unmounting threads on app exit
    def cleanup_threads():
        print("[!] Stopping background listeners safely...")
        keyboard_thread.quit()
        keyboard_thread.wait()

    app.aboutToQuit.connect(cleanup_threads)
    
    keyboard_thread.start()
    hud.show()
    
    print("[DIABLO SYSTEM READY]: Operational state achieved. Execute 'Alt+D' to reveal panel.")
    sys.path.append(PROJECT_ROOT)
    sys.exit(app.exec())

if __name__ == "__main__":
    initialize_diablo_system()