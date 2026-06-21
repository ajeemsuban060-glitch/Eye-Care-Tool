# Eye-Care-Tool
"Context-aware 20-20-20 eye care daemon with activity tracking."
# 👁️ 20-20-20 Eye Care Tool

A context-aware desktop daemon that reminds you to rest your eyes based on **actual active screen time**, not just wall-clock time.

## ✨ Phase 1 Features
- Tracks keyboard and mouse activity via `pynput`.
- Only counts time when you are actively using the computer (pauses when idle).
- Desktop notifications in English and Tamil (locale-aware).
- Logs all sessions and breaks to a local SQLite database.

## 🚀 Installation
1. Clone this repository.
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`

## 🖥️ Usage
Run the tool with:
```bash
python main.py
