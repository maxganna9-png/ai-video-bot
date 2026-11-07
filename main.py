import os
import requests
import telebot
from gtts import gTTS
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

# Render Web Service সচল রাখার জন্য ফ্লাস্ক সার্ভার
app = Flask('')

@app.route('/')
def home():
    return "AI Video Bot is Alive and Running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "স্বাগতম! আপনার এআই ভিডিও ফ্যাক্টরি রেডি। যেকোনো টপিক লিখে পাঠান, আমি শর্টস ভিডিও বানিয়ে দিচ্ছি।")

@bot.message_handler(func=lambda message: True)
def create_ai_video(message):
    topic = message.text
    bot.reply_to(message, f"🎬 '{topic}' এর ওপর ভিডিও তৈরি হচ্ছে। ফ্রী সার্ভার হওয়ায় ১-২ মিনিট সময় লাগতে পারে...")

    audio_file = "voice.mp3"
    video_file = "output_short.mp4"
    bg_video = "bg.mp4"

    try:
        # ১. জেমিনি দিয়ে শর্ট স্ক্রিপ্ট তৈরি (৩০ সেকেন্ডের ছোট স্ক্রিপ্ট যাতে দ্রুত রেন্ডার হয়)
        prompt = f"Write a catchy 30-second YouTube Shorts script about {topic}. Keep it short, interesting, and direct."
        response = ai_client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
        )
        script_text = response.text

        # ২. gTTS দিয়ে দ্রুত ভয়েসওভার তৈরি
        tts = gTTS(text=script_text, lang='en', slow=False)
        tts.save(audio_file)

        # ৩. Pixabay থেকে শর্টস সাইজ বা স্টক ভিডিও ডাউনলোড
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

        # ৪. MoviePy দিয়ে ফাস্ট এডিটিং (fps ও resolution কমিয়ে রেন্ডারিং ফাস্ট করা হয়েছে)
        audio = AudioFileClip(audio_file)
        
        # ভিডিও ক্লিপটি অডিওর সমান ট্রিম করা এবং রিসাইজ করা যাতে সার্ভারে চাপ না পড়ে
        clip = VideoFileClip(bg_video).subclip(0, min(audio.duration, VideoFileClip(bg_video).duration))
        clip = clip.resize(height=720) # সার্ভার ফাস্ট রাখতে 720p রেজুলেশন ব্যবহার করা হয়েছে

        # টেক্সট বা টাইটেল গ্রাফিক্স
        txt_clip = TextClip(topic.upper(), fontsize=45, color='yellow', stroke_color='black', stroke_width=2, size=(700, None), method='caption')
        txt_clip = txt_clip.set_duration(audio.duration).set_position('center')

        # ভিডিও কম্পোজিশন (কম প্রি-সেট দিয়ে দ্রুত রেন্ডার করার ব্যবস্থা)
        final_video = CompositeVideoClip([clip, txt_clip]).set_audio(audio)
        final_video.write_videofile(
            video_file, 
            fps=20, 
            preset='ultrafast',  # ফ্রী সার্ভারের জন্য সবচেয়ে দ্রুত রেন্ডার করার প্রিসেট
            codec='libx264', 
            audio_codec='aac',
            logger=None
        )

        # ৫. টেলিগ্রামে ফাইনাল ভিডিও পাঠানো
        with open(video_file, 'rb') as vid:
            bot.send_video(message.chat.id, vid, caption=f"✅ আপনার এআই শর্টস ভিডিও তৈরি সম্পন্ন!\n📌 টপিক: {topic}")

    except Exception as e:
        bot.reply_to(message, f"❌ একটি ত্রুটি ঘটেছে: {str(e)}")

    finally:
        # ৬. সার্ভার ক্লিনআপ (ফাইলগুলো মুছে ফেলা যাতে স্পেস না ভরে)
        for f in [audio_file, video_file, bg_video]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    
    print("AI Fast Video Bot is running...")
    bot.infinity_polling(none_stop=True, interval=0)
