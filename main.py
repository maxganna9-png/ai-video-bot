import os
import asyncio
import requests
import telebot
import edge_tts
from google import genai
from moviepy.editor import AudioFileClip, VideoFileClip, TextClip, CompositeVideoClip

# Render এর সিক্রেট বক্স থেকে এপিআই কি গুলো নেওয়া হচ্ছে
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "স্বাগতম! আপনার Pixabay ও Gemini চালিত এআই ভিডিও বট রেডি। আমাকে যেকোনো টপিক লিখে পাঠান।")

@bot.message_handler(func=lambda message: True)
def create_ai_video(message):
    topic = message.text
    bot.reply_to(message, f"🤖 '{topic}' এর ওপর কাজ শুরু হয়েছে। স্ক্রিপ্ট ও ভিডিও তৈরি হতে ১-২ মিনিট লাগতে পারে...")

    try:
        audio_file = "voice.mp3"
        video_file = "output_short.mp4"
        bg_video = "bg.mp4"

        # ধাপ ১: Gemini দিয়ে স্ক্রিপ্ট তৈরি
        prompt = f"Write a viral 40-second YouTube Shorts script about {topic}. Make it engaging and fast-paced. No stage directions, only spoken text."
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        script_text = response.text

        # ধাপ ২: Edge-TTS দিয়ে ভয়েসওভার তৈরি
        async def generate_voice():
            communicate = edge_tts.Communicate(script_text, "en-US-ChristopherNeural")
            await communicate.save(audio_file)
        asyncio.run(generate_voice())

        # ধাপ ৩: Pixabay API দিয়ে ভিডিও ডাউনলোড করা
        # এখানে Pixabay এর ভিডিও এন্ডপয়েন্ট ব্যবহার করা হয়েছে
        pixabay_url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={requests.utils.quote(topic)}&orientation=vertical&per_page=3"
        res = requests.get(pixabay_url).json()
        
        if "hits" in res and len(res["hits"]) > 0:
            # মাঝারি সাইজের ভিডিও লিংক নেওয়া
            video_url = res["hits"][0]["videos"]["medium"]["url"]
            video_data = requests.get(video_url)
            with open(bg_video, "wb") as f:
                f.write(video_data.content)
        else:
            bot.reply_to(message, "দুঃখিত, Pixabay-তে এই টপিকের কোনো ভিডিও পাওয়া যায়নি। অন্য টপিক দিয়ে চেষ্টা করুন।")
            return

        # ধাপ ৪: MoviePy দিয়ে ভিডিও ও অডিও এডিট করা
        audio = AudioFileClip(audio_file)
        clip = VideoFileClip(bg_video).subclip(0, min(audio.duration, VideoFileClip(bg_video).duration))
        
        # ভিডিওর ওপর টেক্সট গ্রাফিক্স বসানো
        txt_clip = TextClip(topic.upper(), fontsize=55, color='yellow', stroke_color='black', stroke_width=3, size=(900, None), method='caption')
        txt_clip = txt_clip.set_duration(audio.duration).set_position('center')

        final_video = CompositeVideoClip([clip, txt_clip]).set_audio(audio)
        final_video.write_videofile(video_file, fps=24, codec='libx264', audio_codec='aac')

        # ধাপ ৫: টেলিগ্রামে ভিডিও পাঠানো
        with open(video_file, 'rb') as vid:
            bot.send_video(message.chat.id, vid, caption=f"✅ আপনার এআই শর্টস ভিডিও তৈরি সম্পন্ন!\n📌 টপিক: {topic}")

        # ক্লিনআপ
        os.remove(audio_file)
        os.remove(video_file)
        if os.path.exists(bg_video):
            os.remove(bg_video)

    except Exception as e:
        bot.reply_to(message, f"❌ একটি ত্রুটি ঘটেছে: {str(e)}")

if __name__ == "__main__":
    print("AI Video Bot with Pixabay is running...")
    bot.infinity_polling()
