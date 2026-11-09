import os
import requests
import telebot
from gtts import gTTS
from google import genai
from flask import Flask
from threading import Thread
from moviepy.editor import AudioFileClip, VideoFileClip

# Render পরিবেশ থেকে সিক্রেট কি গুলো নেওয়া
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Render Web Service সচল রাখার জন্য ফ্লাস্ক সার্ভার
app = Flask('')

@app.route('/')
def home():
    return "Fast AI Video Bot is Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "হ্যালো! শর্টস ভিডিওর জন্য টপিক পাঠান, আমি ফাস্ট এআই ভিডিও বানিয়ে দিচ্ছি।")

@bot.message_handler(func=lambda message: True)
def create_ai_video(message):
    topic = message.text
    bot.reply_to(message, f"⚡ '{topic}' নিয়ে ভিডিও প্রসেসিং শুরু হয়েছে...")

    audio_file = "voice.mp3"
    video_file = "output.mp4"
    bg_video = "bg.mp4"

    try:
        # ১. জেমিনি দিয়ে শর্ট ও ফাস্ট স্ক্রিপ্ট তৈরি (gemini-3.5-flash-lite মডেল ব্যবহার করা হয়েছে)
        prompt = f"Write a 20-second punchy script about {topic}. Only spoken text, no extra formatting."
        
        try:
            response = ai_client.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=prompt,
            )
        except Exception:
            # ফলব্যাক হিসেবে অন্য মডেল ব্যবহার করার অপশন
            response = ai_client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt,
            )
            
        script_text = response.text

        # ২. gTTS দিয়ে ভয়েস তৈরি
        tts = gTTS(text=script_text, lang='en', slow=False)
        tts.save(audio_file)

        # ৩. Pixabay থেকে ফাস্ট স্টক ভিডিও ডাউনলোড
        pixabay_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={requests.utils.quote(topic)}&orientation=vertical&per_page=3"
        res = requests.get(pixabay_url).json()
        
        if "hits" in res and len(res["hits"]) > 0:
            video_url = res["hits"][0]["videos"]["small"]["url"]
            video_data = requests.get(video_url)
            with open(bg_video, "wb") as f:
                f.write(video_data.content)
        else:
            bot.reply_to(message, "দুঃখিত, Pixabay-তে এই টপিকের কোনো ভিডিও পাওয়া যায়নি।")
            return

        # ৪. MoviePy দিয়ে দ্রুততম উপায়ে অডিও ও ভিডিও মার্চ করা
        audio = AudioFileClip(audio_file)
        clip = VideoFileClip(bg_video).subclip(0, min(audio.duration, VideoFileClip(bg_video).duration))
        
        final_video = clip.set_audio(audio)
        
        # ultrafast প্রিসেট দিয়ে দ্রুত রেন্ডার করা
        final_video.write_videofile(
            video_file, 
            fps=15, 
            preset='ultrafast', 
            codec='libx264', 
            audio_codec='aac',
            logger=None
        )

        # ৫. টেলিগ্রামে ভিডিও পাঠানো
        with open(video_file, 'rb') as vid:
            bot.send_video(message.chat.id, vid, caption=f"🎬 শর্টস ভিডিও তৈরি সম্পন্ন!\n📌 টপিক: {topic}")

    except Exception as e:
        bot.reply_to(message, f"❌ ত্রুটি ঘটেছে: {str(e)}")

    finally:
        # ৬. সার্ভার ক্লিনআপ
        for f in [audio_file, video_file, bg_video]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    bot.infinity_polling(none_stop=True, interval=0)
