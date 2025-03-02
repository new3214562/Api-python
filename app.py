from flask import Flask, request, jsonify
from flask import send_file
import os
import json
import yt_dlp
from googleapiclient.discovery import build
from datetime import datetime

app = Flask(__name__)

API_KEY = "AIzaSyAa9NgexRNMStPM7jG-cDOqGF74q8s2X14"
HISTORY_FILE = "history.json"
OUTPUT_FOLDER = "downloads"

# โหลดประวัติการดาวน์โหลด
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return []

# บันทึกประวัติ
def save_history(song_info):
    history = load_history()
    history.append(song_info)
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4, ensure_ascii=False)

# ค้นหาวิดีโอ
def search_song(query):
    youtube = build("youtube", "v3", developerKey=API_KEY)
    request = youtube.search().list(part="snippet", q=query, maxResults=1, type="video")
    response = request.execute()

    if not response["items"]:
        return None

    video = response["items"][0]
    video_id = video["id"]["videoId"]
    title = video["snippet"]["title"]
    channel = video["snippet"]["channelTitle"]
    url = f"https://www.youtube.com/watch?v={video_id}"

    return {"title": title, "channel": channel, "url": url, "video_id": video_id}

# ดาวน์โหลดวิดีโอ
def download_video(video_url, file_format):
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    ydl_opts = {
        "format": "bestaudio/best" if file_format == "mp3" else "bestvideo+bestaudio",
        "outtmpl": f"{OUTPUT_FOLDER}/%(title)s.%(ext)s",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}] if file_format == "mp3" else [],
        "quiet": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        filename = ydl.prepare_filename(info_dict)
        
        # ถ้าเป็น mp3, เปลี่ยนนามสกุลไฟล์
        if file_format == "mp3":
            filename = filename.replace(".webm", ".mp3").replace(".m4a", ".mp3")

        return filename

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q")
    if not query:
        return jsonify({"error": "ต้องระบุพารามิเตอร์ 'q'"}), 400

    song_info = search_song(query)
    if not song_info:
        return jsonify({"error": "ไม่พบวิดีโอ"}), 404

    return jsonify(song_info)

@app.route("/download-file", methods=["POST"])
def download_file():
    data = request.json
    video_url = data.get("url")
    file_format = data.get("format", "mp3").lower()

    if not video_url:
        return jsonify({"error": "ต้องระบุพารามิเตอร์ 'url'"}), 400
    if file_format not in ["mp3", "mp4"]:
        return jsonify({"error": "รูปแบบไฟล์ต้องเป็น mp3 หรือ mp4"}), 400

    file_path = download_video(video_url, file_format)

    if not os.path.exists(file_path):
        return jsonify({"error": "ดาวน์โหลดไม่สำเร็จ"}), 500

    return send_file(file_path, as_attachment=True)

@app.route("/history", methods=["GET"])
def history():
    return jsonify(load_history())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
