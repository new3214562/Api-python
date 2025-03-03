import os
import yt_dlp
import json
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler
from googleapiclient.discovery import build
from datetime import datetime

# ตั้งค่าตัวแปร Environment
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
API_KEY = os.environ.get("YOUTUBE_API_KEY")

HISTORY_FILE = "history.json"
OUTPUT_FOLDER = "downloads"

# ตั้งค่า Flask
app = Flask(__name__)
bot_app = Application.builder().token(BOT_TOKEN).build()

# โหลดประวัติการดาวน์โหลด
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return []

# บันทึกประวัติการดาวน์โหลด
def save_history(song_info):
    history = load_history()
    history.append(song_info)
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4, ensure_ascii=False)

# ค้นหาวิดีโอ YouTube ตามชื่อเพลง
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
    channel = response["items"][0]["snippet"]["channelTitle"]
    url = f"https://www.youtube.com/watch?v={video_id}"

    return {"title": title, "channel": channel, "url": url, "video_id": video_id}

# ดาวน์โหลดเพลงจาก YouTube
def download_video(video_url):
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{OUTPUT_FOLDER}/%(title)s.%(ext)s",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
        "quiet": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_url, download=True)
        filename = ydl.prepare_filename(info_dict).replace(".webm", ".mp3").replace(".m4a", ".mp3")
    
    return filename

# คำสั่ง /start
async def start(update: Update, context):
    await update.message.reply_text("🎵 สวัสดี! ใช้ /download <ชื่อเพลง> เพื่อดาวน์โหลด")

# คำสั่ง /download
async def download(update: Update, context):
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("❌ กรุณาระบุชื่อเพลง!")
        return

    song_info = search_song(query)
    if not song_info:
        await update.message.reply_text("❌ ไม่พบเพลงที่ค้นหา!")
        return

    song_info["downloaded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ดาวน์โหลดไฟล์
    file_path = download_video(song_info["url"])

    # ส่งไฟล์ให้ผู้ใช้
    await context.bot.send_document(chat_id=update.effective_chat.id, document=open(file_path, 'rb'))

    # บันทึกประวัติ
    save_history(song_info)

    # แจ้งเตือน
    await update.message.reply_text(f"✅ ดาวน์โหลดเสร็จ: {song_info['title']}")

# คำสั่ง /history
async def history(update: Update, context):
    history = load_history()
    if not history:
        await update.message.reply_text("❌ ไม่มีประวัติการดาวน์โหลด")
        return

    history_message = "📜 ประวัติการดาวน์โหลด:\n"
    for song in history:
        history_message += f"🎵 {song['title']} (ดาวน์โหลดเมื่อ {song['downloaded_at']})\n"

    await update.message.reply_text(history_message)

# ตั้งค่า Webhook
@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), bot_app.bot)
    bot_app.process_update(update)
    return "OK", 200

# ฟังก์ชันหลัก
def main():
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("download", download))
    bot_app.add_handler(CommandHandler("history", history))

    PORT = int(os.environ.get("PORT", 5000))
    bot_app.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=PORT)

# รันบอท
if __name__ == "__main__":
    main()
