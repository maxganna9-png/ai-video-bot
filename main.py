import os
import requests
import telebot
from gtts import gTTS
from google import genai
from flask import Flask
from threading import Thread

# Render পরিবেশ থেকে সিক্রেট কি নেওয়া
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Render Web Service সচল রাখার জন্য ফ্লাস্ক সার্ভার
app = Flask('')

@app.route('/')
def home():
    return "AI Media Separator Bot is Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "স্বাগতম! আমাকে যেকোনো টপিক লিখে পাঠান, আমি ক্যাপকাটে এডিট করার জন্য আলাদা আলাদা 'ভয়েস' ও 'ভিডিও' বানিয়ে দিচ্ছি।")

@bot.message_handler(func=lambda message: True)
def send_media_separately(message):
    topic = message.text
    bot.reply_to(message, f"⚡ '{topic}' এর জন্য স্ক্রিপ্ট, ভয়েস ও ভিডিও আলাদা করা হচ্ছে...")

    audio_file = "voice.mp3"
    bg_video = "bg.mp4"

    try:
        # ১. জেমিনি দিয়ে শর্ট স্ক্রিপ্ট তৈরি
        prompt = f"Write a catchy 30-second YouTube Shorts script about {topic}. Only spoken text, no extra formatting."
        
        response = ai_client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
        )
        script_text = response.text

        # ২. gTTS দিয়ে ভয়েস (অডিও) তৈরি
        tts = gTTS(text=script_text, lang='en', slow=False)
        tts.save(audio_file)

        # ৩. Pixabay থেকে ব্যাকগ্রাউন্ড স্টক ভিডিও ডাউনলোড
        pixabay_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={requests.utils.quote(topic)}&orientation=vertical&per_page=3"
        res = requests.get(pixabay_url).json()
        
        video_downloaded = False
        if "hits" in res and len(res["hits"]) > 0:
            video_url = res["hits"][0]["videos"]["medium"]["url"]
            video_data = requests.get(video_url)
            with open(bg_video, "wb") as f:
                f.write(video_data.content)
            video_downloaded = True

        # ৪. টেলিগ্রামে ভয়েস (Audio) পাঠানো
        with open(audio_file, 'rb') as aud:
            bot.send_audio(message.chat.id, aud, caption=f"🎙️ **এআই ভয়েস ফাইল**\n📌 টপিক: {topic}")

        # ৫. টেলিগ্রামে ভিডিও (Video) পাঠানো (যদি ডাউনলোড হয়ে থাকে)
        if video_downloaded:
            with open(bg_video, 'rb') as vid:
                bot.send_video(message.chat.id, vid, caption=f"🎬 **ব্যাকগ্রাউন্ড স্টক ভিডিও**\n📌 টপিক: {topic}")
        
        # ৬. টেলিগ্রামে স্ক্রিপ্ট টেক্সট পাঠিয়ে দেওয়া (ক্যাপকাটে সাবটাইটেল বসানোর জন্য)
        bot.send_message(message.chat.id, f"📝 **এআই স্ক্রিপ্ট (ক্যাপশনের জন্য):**\n\n{script_text}")

    except Exception as e:
        bot.reply_to(message, f"❌ ত্রুটি ঘটেছে: {str(e)}")

    finally:
        # ৭. সার্ভার ক্লিনআপ
        for f in [audio_file, bg_video]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    
    print("AI Media Separator Bot is running...")
    bot.infinity_polling(none_stop=True, interval=0)
