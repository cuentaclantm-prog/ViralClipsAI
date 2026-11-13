import os, sys, threading, webbrowser
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from paths import OUTPUTS, resource_path
from pipeline import process_video, SUPPORTED_HOSTS

OUTPUTS.mkdir(parents=True, exist_ok=True)
app = Flask(__name__, template_folder=str(resource_path("templates")), static_folder=str(resource_path("static")))
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024

def valid_url(url):
    return url.startswith(("https://", "http://")) and any(h in url.lower() for h in SUPPORTED_HOSTS)

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/process")
def process():
    data = request.get_json(force=True)
    url = (data.get("url") or "").strip()
    length = int(data.get("length", 30))
    style = data.get("style", "dynamic")
    count = int(data.get("count", 3))
    if not valid_url(url):
        return jsonify(error="Pega una URL válida de YouTube, TikTok o Instagram."), 400
    if length not in (15, 30, 45, 60) or style not in ("dynamic", "clean", "podcast"):
        return jsonify(error="Configuración no válida."), 400
    job_id = __import__("uuid").uuid4().hex[:10]
    try:
        result = process_video(url, job_id, length, count, style)
        return jsonify(ok=True, job_id=job_id, clips=result)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.get("/outputs/<path:filename>")
def output_file(filename):
    return send_from_directory(OUTPUTS, filename, as_attachment=True)

def main():
    # Open the local web interface automatically after the server starts.
    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False, threaded=True)

if __name__ == "__main__":
    main()
