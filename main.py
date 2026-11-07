import os
import asyncio
import requests
import telebot
import edge_tts
from google import genai
from flask import Flask
from threading import Thread
from moviepy.editor import AudioFileClip, VideoFileClip, TextClip, CompositeVideoClip

# Render পরিবেশ থেকে সিক্রেট কি গুলো নেওয়া
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Render Web Service-এর পোর্ট বাইন্ডিং ঠিক রাখার জন্য ফ্লাস্ক সার্ভার
app = Flask('')

@app.route('/')
def home():
    return "AI Video Bot is Alive and Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# টেলিগ্রাম বট হ্যান্ডলার
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "স্বাগতম! আপনার ফ্রী এআই ভিডিও বট রেডি। আমাকে যেকোনো টপিক লিখে পাঠান।")

@bot.message_handler(func=lambda message: True)
def create_ai_video(message):
    topic = message.text
    bot.reply_to(message, f"🤖 '{topic}' এর ওপর কাজ শুরু হয়েছে। ভিডিও তৈরি হতে ১-২ মিনিট লাগতে পারে...")

    try:
        audio_file = "voice.mp3"
        video_file = "output_short.mp4"
        bg_video = "bg.mp4"

        # ১. জেমিনি দিয়ে স্ক্রিপ্ট তৈরি
        prompt = f"Write a viral 40-second YouTube Shorts script about {topic}. Make it engaging and fast-paced. No stage directions, only spoken text."
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        script_text = response.text

        # ২. ভয়েসওভার তৈরি
        async def generate_voice():
            communicate = edge_tts.Communicate(script_text, "en-US-ChristopherNeural")
            await communicate.save(audio_file)
        asyncio.run(generate_voice())

        # ৩. Pixabay থেকে ভিডিও ডাউনলোড
        pixabay_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={requests.utils.quote(topic)}&orientation=vertical&per_page=3"
        res = requests.get(pixabay_url).json()
        
        if "hits" in res and len(res["hits"]) > 0:
            video_url = res["hits"][0]["videos"]["medium"]["url"]
            video_data = requests.get(video_url)
            with open(bg_video, "wb") as f:
                f.write(video_data.content)
        else:
            bot.reply_to(message, "দুঃখিত, Pixabay-তে এই টপিকের কোনো ভিডিও পাওয়া যায়নি।")
            return

        # ৪. MoviePy দিয়ে ভিডিও এডিটিং
        audio = AudioFileClip(audio_file)
        clip = VideoFileClip(bg_video).subclip(0, min(audio.duration, VideoFileClip(bg_video).duration))
        
        txt_clip = TextClip(topic.upper(), fontsize=55, color='yellow', stroke_color='black', stroke_width=3, size=(900, None), method='caption')
        txt_clip = txt_clip.set_duration(audio.duration).set_position('center')

        final_video = CompositeVideoClip([clip, txt_clip]).set_audio(audio)
        final_video.write_videofile(video_file, fps=24, codec='libx264', audio_codec='aac')

        # ৫. টেলিগ্রামে পাঠানো
        with open(video_file, 'rb') as vid:
            bot.send_video(message.chat.id, vid, caption=f"✅ আপনার শর্টস ভিডিও তৈরি সম্পন্ন!\n📌 টপিক: {topic}")

        # ক্লিনআপ
        os.remove(audio_file)
        os.remove(video_file)
        if os.path.exists(bg_video):
            os.remove(bg_video)

    except Exception as e:
        bot.reply_to(message, f"❌ একটি ত্রুটি ঘটেছে: {str(e)}")

if __name__ == "__main__":
    # ফ্লাস্ক সার্ভারকে ব্যাকগ্রাউন্ডে রান করানো যাতে Render পোর্ট এরর না দেয়
    t = Thread(target=run_flask)
    t.start()
    
    print("AI Video Bot is running via Web Service...")
    bot.infinity_polling(none_stop=True, interval=0)
