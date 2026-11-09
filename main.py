import os
import requests
import telebot
from gtts import gTTS
from flask import Flask
from threading import Thread

# Render পরিবেশ থেকে সিক্রেট কি নেওয়া
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Render Web Service সচল রাখার জন্য ফ্লাস্ক সার্ভার
app = Flask('')

@app.route('/')
def home():
    return "Multi-Command AI Bot is Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# /start কমান্ড হ্যান্ডলার
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "🤖 **এআই মিডিয়া বটে স্বাগতম!**\n\n"
        "আপনি আমাকে বিভিন্ন কমান্ড দিতে পারেন:\n"
        "• সরাসরি যেকোনো টপিক (যেমন: `Ocean`) লিখে পাঠান ➔ আমি **ভয়েস ও ভিডিও দুটোই** আলাদাভাবে দেবো।\n"
        "• `/audio <টপিক>` ➔ শুধু ভয়েস (অডিও) পাওয়ার জন্য।\n"
        "• `/video <টপিক>` ➔ শুধু স্টক ভিডিও পাওয়ার জন্য।\n"
        "• `/help` ➔ সাহায্য বা নির্দেশিকা দেখার জন্য।"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# /help কমান্ড হ্যান্ডলার
@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "📖 **বট ব্যবহারের নিয়ম:**\n\n"
        "1️⃣ **কম্বো কমান্ড:** শুধু লিখে পাঠান `Elon Musk`। বট তার ভয়েস এবং ভিডিও দুটোই দিয়ে দেবে।\n"
        "2️⃣ **শুধু অডিও:** লিখুন `/audio Coding tips`\n"
        "3️⃣ **শুধু ভিডিও:** লিখুন `/video Rain falling`\n\n"
        "এগুলো ডাউনলোড করে আপনি CapCut বা যেকোনো এডিটরে ব্যবহার করতে পারবেন!"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

# /audio কমান্ড হ্যান্ডলার (শুধু ভয়েস নেওয়ার জন্য)
@bot.message_handler(commands=['audio'])
def handle_audio_command(message):
    # কমান্ডের পরের অংশটুকু টপিক হিসেবে নেওয়া (যেমন: /audio cat থেকে 'cat' আলাদা করা)
    topic = message.text.replace("/audio", "").strip()
    if not topic:
        bot.reply_to(message, "⚠️ দয়া করে কমান্ডের সাথে একটি টপিক লিখুন। যেমন: `/audio Volcano`", parse_mode="Markdown")
        return

    bot.reply_to(message, f"🎙️ '{topic}' এর জন্য ভয়েস তৈরি হচ্ছে...")
    audio_file = "voice.mp3"
    try:
        script_text = f"Fascinating facts and amazing details about {topic}. Everything you need to know."
        tts = gTTS(text=script_text, lang='en', slow=False)
        tts.save(audio_file)

        with open(audio_file, 'rb') as aud:
            bot.send_audio(message.chat.id, aud, caption=f"🎙️ **ভয়েস ফাইল:** {topic}")
    except Exception as e:
        bot.reply_to(message, f"❌ ত্রুটি: {str(e)}")
    finally:
        if os.path.exists(audio_file):
            os.remove(audio_file)

# /video কমান্ড হ্যান্ডলার (শুধু ভিডিও নেওয়ার জন্য)
@bot.message_handler(commands=['video'])
def handle_video_command(message):
    topic = message.text.replace("/video", "").strip()
    if not topic:
        bot.reply_to(message, "⚠️ দয়া করে কমান্ডের সাথে একটি টপিক লিখুন। যেমন: `/video Ocean waves`", parse_mode="Markdown")
        return

    bot.reply_to(message, f"🎬 '{topic}' এর জন্য স্টক ভিডিও খোঁজা হচ্ছে...")
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
                bot.send_video(message.chat.id, vid, caption=f"🎬 **স্টক ভিডিও:** {topic}")
        else:
            bot.reply_to(message, "⚠️ এই টপিকের কোনো স্টক ভিডিও পাওয়া যায়নি।")
    except Exception as e:
        bot.reply_to(message, f"❌ ত্রুটি: {str(e)}")
    finally:
        if os.path.exists(bg_video):
            os.remove(bg_video)

# সাধারণ লেখা বা টপিক পাঠালে একসাথে ভয়েস ও ভিডিও দুটোই দেওয়ার হ্যান্ডলার
@bot.message_handler(func=lambda message: True)
def handle_text_message(message):
    topic = message.text.strip()
    if topic.startswith("/"):
        bot.reply_to(message, "⚠️ অজানা কমান্ড! সাহায্য পেতে `/help` লিখুন।")
        return

    bot.reply_to(message, f"⚡ '{topic}' এর জন্য ভয়েস এবং ভিডিও তৈরি হচ্ছে...")

    audio_file = "voice.mp3"
    bg_video = "bg.mp4"

    try:
        # ১. ভয়েস তৈরি
        script_text = f"Fascinating facts and amazing details about {topic}. Everything you need to know."
        tts = gTTS(text=script_text, lang='en', slow=False)
        tts.save(audio_file)

        # ২. ভিডিও ডাউনলোড
        pixabay_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={requests.utils.quote(topic)}&orientation=vertical&per_page=3"
        res = requests.get(pixabay_url).json()
        
        video_downloaded = False
        if "hits" in res and len(res["hits"]) > 0:
            video_url = res["hits"][0]["videos"]["medium"]["url"]
            video_data = requests.get(video_url)
            with open(bg_video, "wb") as f:
                f.write(video_data.content)
            video_downloaded = True

        # ৩. টেলিগ্রামে পাঠানো
        with open(audio_file, 'rb') as aud:
            bot.send_audio(message.chat.id, aud, caption=f"🎙️ **ভয়েস ফাইল**\n📌 টপিক: {topic}")

        if video_downloaded:
            with open(bg_video, 'rb') as vid:
                bot.send_video(message.chat.id, vid, caption=f"🎬 **স্টক ভিডিও**\n📌 টপিক: {topic}")
        else:
            bot.reply_to(message, "⚠️ ভয়েস পাঠানো হয়েছে, তবে এই টপিকের কোনো স্টক ভিডিও পাওয়া যায়নি।")

    except Exception as e:
        bot.reply_to(message, f"❌ ত্রুটি ঘটেছে: {str(e)}")

    finally:
        if os.path.exists(audio_file):
            os.remove(audio_file)
        if os.path.exists(bg_video):
            os.remove(bg_video)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    
    print("Multi-Command AI Bot is running...")
    bot.infinity_polling(none_stop=True, interval=0)
