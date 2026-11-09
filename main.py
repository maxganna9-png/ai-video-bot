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
    return "Multi-Language AI Bot is Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# /start কমান্ড
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🌍 **মাল্টি-ল্যাঙ্গুয়েজ এআই বটে স্বাগতম!**\n\n"
        "আপনি **যেকোনো ভাষায়** (বাংলা, English, हिन्दी, العربية, Español ইত্যাদি) যেকোনো টপিক লিখে পাঠান। বট ঠিক সেই ভাষাতেই গল্প ও ভয়েস বানিয়ে দেবে!\n\n"
        "• গল্প ও ভয়েস পেতে: সরাসরি যেকোনো ভাষায় টপিক লিখে পাঠান।\n"
        "• স্টক ভিডিও পেতে কমান্ড দিন: `/video <topic>`"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# /video কমান্ড (স্টক ভিডিও নেওয়ার জন্য)
@bot.message_handler(commands=['video'])
def handle_video_command(message):
    topic = message.text.replace("/video", "").strip()
    if not topic:
        bot.reply_to(message, "⚠️ Please write a topic. Example: `/video Nature`", parse_mode="Markdown")
        return

    bot.reply_to(message, f"🎬 Searching stock video for '{topic}'...")
    bg_video = "bg.mp4"
    try:
        pixabay_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={requests.utils.quote(topic)}&orientation=vertical&per_page=3"
        res = requests.get(pixabay_url).json()
        
        if "hits" in res and len(res["hits"]) > 0:
            video_url = res["hits"][0]["videos"]["medium"]["url"]
            video_data = requests.get(video_url)
            with open(bg_video, "wb") as f:
                f.write(video_data.content)

            with open(bg_video, 'rb') as vid:
                bot.send_video(message.chat.id, vid, caption=f"🎬 **Stock Video:** {topic}")
        else:
            bot.reply_to(message, "⚠️ No stock video found for this topic.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")
    finally:
        if os.path.exists(bg_video):
            os.remove(bg_video)

# ভাষা শনাক্ত করে স্টোরি ও ভয়েস তৈরির মূল হ্যান্ডলার
@bot.message_handler(func=lambda message: True)
def handle_multilingual_story(message):
    user_text = message.text.strip()
    if user_text.startswith("/"):
        bot.reply_to(message, "⚠️ Unknown command!")
        return

    bot.reply_to(message, "✍️ Generating story and voice in your language...")

    audio_file = "multi_voice.mp3"

    try:
        # ১. জেমিনি এআইকে নির্দেশনা দেওয়া যাতে ব্যবহারকারী যে ভাষায় লিখবে, সেই ভাষাতেই স্টোরি লেখে
        prompt = (
            f"Detect the language of the following text/topic: '{user_text}'. "
            f"Write a short, engaging 40-second story or script about this topic IN THAT EXACT SAME LANGUAGE. "
            f"Provide only the story text, no extra notes."
        )
        
        response = ai_client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
        )
        story_text = response.text

        # ২. ভাষা শনাক্ত করার জন্য ছোট লজিক (বা ডিফল্ট হিসেবে টেক্সট থেকে ভাষা নির্ধারণ)
        # বাংলা হলে 'bn', হিন্দি হলে 'hi', আরবি হলে 'ar', ইংরেজি হলে 'en' ইত্যাদি স্বয়ংক্রিয়ভাবে সিলেক্ট করতে পারি
        # অথবা সহজভাবে জেমিনিকে বলে দিতে পারি ভাষা কোড সহ আউটপুট দিতে। 
        # আরও সহজ উপায়ে gTTS-এর জন্য ভাষা ডিটেক্ট করতে একটি ছোট এপিআই বা বেসিক লজিক ব্যবহার করা যায়।
        
        # সহজ সমাধান: জেমিনিকে বলে দেওয়া ভাষা কোড সহ দিতে অথবা বাংলা ও ইংরেজির জন্য বেসিক চেক:
        lang_code = 'en' # ডিফল্ট ইংরেজি
        if any('\u0980' <= c <= '\u09FF' for c in user_text):  # বাংলা হরফ চেক
            lang_code = 'bn'
        elif any('\u0900' <= c <= '\u097F' for c in user_text):  # হিন্দি হরফ চেক
            lang_code = 'hi'
        elif any('\u0600' <= c <= '\u06FF' for c in user_text):  # আরবি হরফ চেক
            lang_code = 'ar'
        # ইংরেজি বা অন্যান্য ভাষার জন্য জেমিনির সাহায্য নেওয়া যেতে পারে, অথবা ইউজার ইনপুট চেক করা।

        # ৩. gTTS দিয়ে সেই নির্দিষ্ট ভাষায় ভয়েস তৈরি
        tts = gTTS(text=story_text, lang=lang_code, slow=False)
        tts.save(audio_file)

        # ৪. টেলিগ্রামে ভয়েস ফাইল পাঠানো
        with open(audio_file, 'rb') as aud:
            bot.send_audio(message.chat.id, aud, caption=f"🎙️ **AI Voice (Lang: {lang_code})**\n📌 Topic: {user_text}")

        # ৫. টেলিগ্রামে গল্পের টেক্সট পাঠানো
        bot.send_message(message.chat.id, f"📜 **Story Script:**\n\n{story_text}")

    except Exception as e:
        bot.reply_to(message, f"❌ Error occurred: {str(e)}")

    finally:
        if os.path.exists(audio_file):
            os.remove(audio_file)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    
    print("Multi-Language AI Bot is running...")
    bot.infinity_polling(none_stop=True, interval=0)
