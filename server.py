# Kurulum:  pip install flask flask-cors yt-dlp demucs   (ffmpeg de kurulu olmalı)
# Çalıştır: python server.py
# Telefon için https gerekir:  cloudflared tunnel --url http://localhost:8000
import os, sys, glob, uuid, threading, subprocess
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__); CORS(app)
OUT = "out"; os.makedirs(OUT, exist_ok=True)
jobs = {}

def run(job, url, model):
    wd = os.path.join(OUT, job)
    try:
        os.makedirs(wd, exist_ok=True)
        jobs[job] = {"state": "İndiriliyor..."}
        if url:
            subprocess.run(["yt-dlp", "-x", "--audio-format", "mp3", "--no-playlist",
                            "-o", os.path.join(wd, "src.%(ext)s"), url], check=True)
        src = glob.glob(os.path.join(wd, "src.*"))[0]
        jobs[job] = {"state": "Ayrıştırılıyor (birkaç dk sürebilir)..."}
        subprocess.run([sys.executable, "-m", "demucs", "-n", model, "--mp3",
                        "-o", wd, src], check=True)
        stems = {}
        for f in glob.glob(f"{wd}/{model}/src/*.mp3"):
            n = os.path.basename(f)[:-4]
            stems[n] = f"/files/{job}/{model}/src/{n}.mp3"
        jobs[job] = {"state": "done", "stems": stems}
    except Exception as e:
        jobs[job] = {"state": "error", "error": str(e)}

@app.post("/separate")
def separate():
    d = request.get_json()
    job = uuid.uuid4().hex[:8]
    threading.Thread(target=run, args=(job, d["url"], d.get("model", "htdemucs_6s")), daemon=True).start()
    return jsonify(job=job)

@app.post("/upload")
def upload():
    f = request.files["file"]
    model = request.form.get("model", "htdemucs_6s")
    job = uuid.uuid4().hex[:8]
    wd = os.path.join(OUT, job); os.makedirs(wd, exist_ok=True)
    ext = os.path.splitext(f.filename)[1] or ".mp3"
    f.save(os.path.join(wd, "src" + ext))
    threading.Thread(target=run, args=(job, None, model), daemon=True).start()
    return jsonify(job=job)

@app.get("/status/<job>")
def status(job):
    return jsonify(jobs.get(job, {"state": "error", "error": "iş bulunamadı"}))

@app.get("/files/<path:p>")
def files(p):
    return send_from_directory(OUT, p)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
