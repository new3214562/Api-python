from flask import Flask, request, send_file
import os
import yt_dlp
from googleapiclient.discovery import build

app = Flask(__name__)

# ตั้งค่า YouTube API Key
API_KEY = "AIzaSyAa9NgexRNMStPM7jG-cDOqGF74q8s2X14"
OUTPUT_FOLDER = "downloads"

# ค้นหาเพลงใน YouTube
def search_song(query):
    youtube = build("youtube", "v3", developerKey=API_KEY)
    request = youtube.search().list(
        part="snippet",
        q=query,
        maxResults=1,
        type="video"
    )
    response = request.execute()

    if not response["items"]:
        return None

    video_id = response["items"][0]["id"]["videoId"]
    title = response["items"][0]["snippet"]["title"]
    url = f"https://www.youtube.com/watch?v={video_id}"

    return {"title": title, "url": url, "video_id": video_id}

# ดาวน์โหลดวิดีโอ/เพลงจาก YouTube
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
        
        # เปลี่ยนนามสกุลไฟล์ถ้าเป็น MP3
        if file_format == "mp3":
            filename = filename.replace(".webm", ".mp3").replace(".m4a", ".mp3")

        return filename

# API `/download-file` ใช้ GET
@app.route("/download-file", methods=["GET"])
def download_file():
    query = request.args.get("query")
    file_format = request.args.get("format", "mp3").lower()

    if not query:
        return "Error: ต้องระบุพารามิเตอร์ 'query'", 400
    if file_format not in ["mp3", "mp4"]:
        return "Error: รูปแบบไฟล์ต้องเป็น mp3 หรือ mp4", 400

    # 1. ค้นหาเพลง
    song_info = search_song(query)
    if not song_info:
        return "Error: ไม่พบเพลงที่ค้นหา!", 404

    # 2. ดาวน์โหลดเพลง
    file_path = download_video(song_info["url"], file_format)

    if not os.path.exists(file_path):
        return "Error: ดาวน์โหลดไม่สำเร็จ", 500

    # 3. ส่งไฟล์กลับให้ผู้ใช้
    return send_file(file_path, as_attachment=True)

# รัน API
if __name__ == "__main__":
    app.run(debug=True)
