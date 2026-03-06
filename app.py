from flask import Flask, render_template, request, jsonify, Response
import speech_recognition as sr
from deep_translator import GoogleTranslator
import threading
import queue
import time
import json

app = Flask(__name__)

# ── original backend code (unchanged) ──────────────────────────────────────

LANGUAGE_CODES = {
    'Hindi':    'hi-IN',
    'Japanese': 'ja-JP',
    'Punjabi':  'pa-IN',
    'Korean':   'ko-KR',
    'German':   'de-DE',
    'Spanish':  'es-ES',
    'French':   'fr-FR',
    'Marathi':  'mr-IN',
    'Gujarati': 'gu-IN'
}

# ── shared state ────────────────────────────────────────────────────────────

event_queue: queue.Queue = queue.Queue()
listen_thread: threading.Thread | None = None
stop_flag = threading.Event()


def push(event_type: str, **kwargs):
    event_queue.put({"type": event_type, **kwargs})


def listen_loop(language: str):
    """Runs in a background thread; mirrors the original while-loop logic."""
    recognizer = sr.Recognizer()
    language_code = LANGUAGE_CODES[language]

    try:
        microphone = sr.Microphone()
    except Exception as e:
        push("error", message=f"Microphone init failed: {e}")
        return

    push("status", message="Calibrating microphone for ambient noise…")
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)

    push("status", message="Listening…")

    while not stop_flag.is_set():
        with microphone as source:
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                if stop_flag.is_set():
                    break

                push("status", message="Recognising…")
                recognized_text = recognizer.recognize_google(audio, language=language_code)
                push("recognised", language=language, text=recognized_text)

                translator = GoogleTranslator(source='auto', target='en')
                translated_text = translator.translate(recognized_text)
                push("translated", text=translated_text)
                push("status", message="Listening…")

            except sr.WaitTimeoutError:
                pass   # just loop again
            except sr.UnknownValueError:
                push("status", message="Could not understand audio – speak again…")
            except sr.RequestError as e:
                push("error", message=f"Speech service error: {e}")
            except Exception as e:
                if not stop_flag.is_set():
                    push("error", message=str(e))

# ── routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", languages=list(LANGUAGE_CODES.keys()))


@app.route("/start", methods=["POST"])
def start():
    global listen_thread
    data = request.get_json()
    language = data.get("language", "")

    if language not in LANGUAGE_CODES:
        return jsonify({"error": f"Unsupported language: {language}"}), 400

    # stop any previous session
    stop_flag.set()
    if listen_thread and listen_thread.is_alive():
        listen_thread.join(timeout=3)

    # drain queue
    while not event_queue.empty():
        try:
            event_queue.get_nowait()
        except queue.Empty:
            break

    stop_flag.clear()
    listen_thread = threading.Thread(target=listen_loop, args=(language,), daemon=True)
    listen_thread.start()
    return jsonify({"status": "started", "language": language})


@app.route("/stop", methods=["POST"])
def stop():
    stop_flag.set()
    return jsonify({"status": "stopped"})


@app.route("/events")
def events():
    """Server-Sent Events stream consumed by the frontend."""
    def generate():
        while True:
            try:
                event = event_queue.get(timeout=20)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                yield "data: {\"type\":\"ping\"}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
