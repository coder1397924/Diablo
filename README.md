# DIABLO 🔥
### A Hybrid AI Desktop Assistant (Online + Offline Mode)

![Status](https://img.shields.io/badge/status-stable-green)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.10+-blue)

DIABLO is a powerful, privacy-focused desktop assistant that combines **cloud intelligence** (Groq) with **local offline capabilities** (Ollama). It features native tool execution, vision analysis, and a sleek dark-themed UI.

---

## 🚀 Features

- ✅ **Hybrid Engine**: Seamlessly switches between Cloud (Groq) and Local (Ollama) models.
- ✅ **Offline Mode**: Works without internet using local LLMs.
- ✅ **Vision Support**: Analyze screenshots with `/see` command (Cloud).
- ✅ **Code Execution**: Safe Python sandbox with `>>` command.
- ✅ **System Control**: Execute shell commands with `>` command.
- ✅ **File Context**: Attach files for AI analysis.
- ✅ **Hotkeys**: Global hotkeys for instant access (`Alt+D`).
- ✅ **Dark UI**: Developer-focused interface with syntax highlighting.

---

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/coder1397924/Diablo.git
cd Diablo
```

### 2. Create Virtual Environment
```bash
python -m venv diablo_env
diablo_env\Scripts\activate
```
### 3. Install Dependencies
pip install -r requirements.txt

### 4. Configure Environment
Create a .env file in the root directory:
```bash
GROQ_API_KEY=your_groq_api_key_here
OLLAMA_DEFAULT_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://localhost:11434/api/chat
FORCE_OFFLINE=false
REQUEST_TIMEOUT=60
HOTKEY_REVEAL=alt+d
HOTKEY_TERMINATE=win+esc
```

### 5. Run Diablo
```bash
python main.py
```

### Offline Mode Setup
To use Diablo without internet, you need Ollama installed locally.

1. Install Ollama: https://ollama.com/
2. Pull the Model:
```bash
ollama pull llama3.2:3b
```
3. Start Server:
```bash
ollama serve
```

### Usage Commands
```bash
Command	  Description	    Example
hello	  Standard chat	    hello
>	      Shell command	    >dir
>>	      Python code	    >>print(2+2)
/see	  Vision analysis	/see what's on my screen
attach	  File context	    Click 📎 button

-Hotkeys
1. Alt + D: Show/Hide Diablo HUD
2. Win + Esc: Shutdown Diablo
3. Esc: Hide HUD (when focused)

### 🛠️ Building from Source

To create a standalone executable:

pip install pyinstaller
pyinstaller --clean --noconfirm --onefile --windowed --name Diablo --collect-all PyQt6 main.py
```
The executable will be in dist/Diablo.exe.

### 📁 Project Structure
```bash
diablo/
├── core/           # Engine, Memory, DMM, Config
├── interface/      # GUI, Styles
├── services/       # Tools, Vision, File Manager
├── main.py         # Entry Point
├── requirements.txt
└── README.md
```

### ⚠️ Important Notes
- API Keys: Never commit your .env file to GitHub.
- Ollama: Required for offline mode. Must be running locally.
- Permissions: Run as Administrator if hotkeys fail on Windows.

### Contributing
Contributions are welcome! Please open an issue or submit a pull request.

### Developed by Alok
