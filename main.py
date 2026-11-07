import os
import asyncio
import requests
import telebot
import edge_tts
from google import genai
from moviepy.editor import AudioFileClip, VideoFileClip, TextClip, CompositeVideoClip

# --- আপনার এপিআই কি (API Keys) এখানে বসান ---
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
PEXELS_API_KEY = "YOUR_PEXELS_API_KEY"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"  # Google AI Studio থেকে ফ্রীতে পাবেন

bot = telebot.TeleBot(TELEGRAM_TOKEN)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "স্বাগতম! আপনার এআই ভিডিও ফ্যাক্টরি রেডি। আমাকে যেকোনো টপিক বা বিষয়ের নাম লিখে পাঠান।")

@bot.message_handler(func=lambda message: True)
def create_ai_video(message):
    topic = message.text
    bot.reply_to(message, f"🤖 '{topic}' এর ওপর এআই স্ক্রিপ্ট লেখা ও ভিডিও প্রসেসিং শুরু হয়েছে...")

    try:
        audio_file = "voice.mp3"
        video_file = "output_short.mp4"
        bg_video = "bg.mp4"

        # ধাপ ১: Gemini API দিয়ে ফ্রীতে আকর্ষণীয় স্ক্রিপ্ট তৈরি করানো
        prompt = f"Write a viral 40-second YouTube Shorts script about {topic}. Make it engaging and fast-paced. Do not include any stage directions, only the spoken script text."
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        script_text = response.text
        print(f"Generated Script: {script_text}")

        # ধাপ ২: Edge-TTS দিয়ে ভয়েসওভার (Audio) তৈরি করা
        async def generate_voice():
            communicate = edge_tts.Communicate(script_text, "en-US-ChristopherNeural")
            await communicate.save(audio_file)
        asyncio.run(generate_voice())

        # ধাপ ৩: Pexels API দিয়ে ফ্রী স্টক ভিডিও ডাউনলোড করা
        headers = {"Authorization": PEXELS_API_KEY}
        pex_url = f"https://api.pexels.com/videos/search?query={topic}&per_page=1&orientation=portrait"
        res = requests.get(pex_url, headers=headers).json()
        
        if "videos" in res and len(res["videos"]) > 0:
            download_url = res["videos"][0]["video_files"][0]["link"]
            video_data = requests.get(download_url)
            with open(bg_video, "wb") as f:
                f.write(video_data.content)
        else:
            bot.reply_to(message, "দুঃখিত, এই টপিকের কোনো স্টক ভিডিও ইন্টারনেটে পাওয়া যায়নি। অন্য টপিক দিয়ে চেষ্টা করুন।")
            return

        # ধাপ ৪: MoviePy দিয়ে ভিডিও এডিটিং, ভয়েস ও টেক্সট গ্রাফিক্স যুক্ত করা
        audio = AudioFileClip(audio_file)
        clip = VideoFileClip(bg_video).subclip(0, min(audio.duration, VideoFileClip(bg_video).duration))
        
        # ভিডিওর ওপর সুন্দর টেক্সট বা টাইটেল গ্রাফিক্স বসানো
        txt_clip = TextClip(topic.upper(), fontsize=55, color='yellow', stroke_color='black', stroke_width=3, size=(900, None), method='caption')
        txt_clip = txt_clip.set_duration(audio.duration).set_position('center')

        # সব একসাথে কম্পোজ করা
        final_video = CompositeVideoClip([clip, txt_clip]).set_audio(audio)
        final_video.write_videofile(video_file, fps=24, codec='libx264', audio_codec='aac')

        # ধাপ ৫: টেলিগ্রামে ফাইনাল ভিডিও ফাইলটি পাঠিয়ে দেওয়া
        with open(video_file, 'rb') as vid:
            bot.send_video(message.chat.id, vid, caption=f"✅ আপনার এআই শর্টস ভিডিও তৈরি সম্পন্ন!\n📌 টপিক: {topic}")

        # ক্লিনআপ (সার্ভার থেকে ফ্রী ফাইলগুলো মুছে ফেলা)
        os.remove(audio_file)
        os.remove(video_file)
        if os.path.exists(bg_video):
            os.remove(bg_video)

    except Exception as e:
        bot.reply_to(message, `❌ একটি ত্রুটি ঘটেছে: {str(e)}`)

if __name__ == "__main__":
    print("AI Video Bot is running...")
    bot.infinity_polling()
