import logging
import os
import uuid
import time
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from moviepy.editor import VideoFileClip, AudioFileClip
from gtts import gTTS
from deep_translator import GoogleTranslator
import openai
from dotenv import load_dotenv
import nest_asyncio

nest_asyncio.apply()
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Menga video yuboring, men uni o‘zbek tiliga tarjima qilib, yangi ovoz bilan qaytaraman.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    if not video:
        await update.message.reply_text("Iltimos, video yuboring.")
        return

    file = await context.bot.get_file(video.file_id)
    file_name = f"{uuid.uuid4()}.mp4"
    await file.download_to_drive(file_name)
    await update.message.reply_text("✅ Video yuklandi. Ishlov berilmoqda...")

    try:
        times = {}

        t0 = time.time()
        video_clip = VideoFileClip(file_name)
        audio_path = file_name.replace(".mp4", ".wav")
        video_clip.audio.write_audiofile(audio_path)
        times["🎧 Audio ajratish"] = time.time() - t0
        await update.message.reply_text("🎧 Audio ajratildi.")

        await update.message.reply_text("📜 Matnga aylantirilmoqda...")
        t0 = time.time()
        with open(audio_path, "rb") as audio_file:
            transcript = openai.audio.transcribe(model="whisper-1", file=audio_file)
        times["📜 Transkriptsiya"] = time.time() - t0

        await update.message.reply_text("🌐 O‘zbek tiliga tarjima qilinmoqda...")
        t0 = time.time()
        uz_text = GoogleTranslator(source='auto', target='uz').translate(transcript['text'])
        times["🌐 Tarjima"] = time.time() - t0

        await update.message.reply_text("🔊 Ovoz yaratilmoqda...")
        t0 = time.time()
        tts = gTTS(uz_text, lang="uz")
        mp3_path = file_name.replace(".mp4", "_uz.mp3")
        tts.save(mp3_path)
        times["🔊 Ovoz yaratish"] = time.time() - t0

        await update.message.reply_text("🎞 Yangi video tayyorlanmoqda...")
        t0 = time.time()
        new_audio = AudioFileClip(mp3_path)
        final_video = video_clip.set_audio(new_audio)
        output_path = file_name.replace(".mp4", "_final.mp4")
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        times["🎞 Video yaratish"] = time.time() - t0

        await update.message.reply_text("✅ Tayyor! Mana tarjima qilingan video:")
        await update.message.reply_video(video=open(output_path, 'rb'))

        timing_message = "\n".join([f"{k}: {v:.2f} sek" for k, v in times.items()])
        await update.message.reply_text("⏱ Ish vaqti:\n" + timing_message)

    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {str(e)}")

    finally:
        try:
            video_clip.close()
            new_audio.close()
        except:
            pass
        for f in [file_name, audio_path, mp3_path, output_path]:
            if os.path.exists(f):
                os.remove(f)

async def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    print("🤖 Bot ishga tushdi.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(run_bot())
