# VoiceBridge – Real-time Voice Translator

A web frontend for the real-time voice translator project.  
The original backend logic is **completely unchanged** — it is simply wrapped in a small Flask server.

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## How it works

| File | Role |
|---|---|
| `app.py` | Flask server — wraps the original translator in API endpoints |
| `templates/index.html` | Frontend UI |

The frontend communicates with the backend via:
- `POST /start` — begin listening in a chosen language
- `POST /stop`  — stop listening
- `GET  /events` — Server-Sent Events stream for live status, recognised text & translations

## Notes
- Your microphone must be accessible to the Python process.
- An active internet connection is required (Google Speech Recognition + DeepTranslator).
