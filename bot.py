import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

TOKEN = os.environ.get("TELEGRAM_TOKEN", "ضع_التوكن_هنا")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🏴 **مَكْتَبَةُ الأَنَاشِيدِ الجِهَادِيَّةِ** 🏴\n\n"
        "\"إِنَّ مِنَ البَيَانِ لَسِحْراً، وَإِنَّ مِنَ الشِّعْرِ لَحِكْمَةً\"\n\n"
        "مرحباً بك في منبر الكلمة الصادقة واللحن الحادي. أرسل الآن **اسم الأنشودة**، "
        "لتبحر في مكتبة تجمع بين زئير الصوتيات وعز المرتجيات بصيغتي الصوت والفيديو.\n\n"
        "ーーー\n"
        "**وفي ظلال هذا الصرح، تحيةٌ معطرة بعبق المجد لأميرة البيت وعنوان الثبات: (الأندلسية)** 🪶\n\n"
        "هِيَ الأَنْدَلُسِيَّةُ فِي لَهِيبِ المَعَامِعِ المَجْدُ مَسْكَنُهَا\n"
        "سَلِيلَةُ عِزٍّ بِالعَقِيدَةِ وَالفِدَا تَسْمُو بِمَوْطِنِهَا\n\n"
        "خَاضَتْ فِجَاجَ الحَرْبِ ثَابِتَةَ الخُطَى لَا تَنْثَنِي\n"
        "زَوْجٌ كَمِثْلِ السَّيْفِ فِي كَفِّ الـمُجَاهِدِ مَعْدِنُهَا"
    )
    await update.message.reply_text(text=welcome_text, parse_mode="Markdown")

# دالة البحث في يوتيوب (أسرع وأضمن)
def search_youtube_results(query):
    ydl_opts = {
        'default_search': 'ytsearch3',  # البحث في يوتيوب وجلب أول 3 نتائج
        'quiet': True,
        'noplaylist': True,
        'extract_flat': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"أنشودة {query}", download=False) # يضيف كلمة أنشودة تلقائياً لضمان الدقة
        if 'entries' in info:
            return info['entries'][:3]
        return []

def download_media(url, download_type):
    if download_type == "audio":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True
        }
    else:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if download_type == "audio":
            actual_filename = os.path.splitext(filename)[0] + ".mp3"
        else:
            actual_filename = filename
        return actual_filename, info.get('title', 'أنشودة مستخرجة')

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if len(query) < 2:
        await update.message.reply_text("يرجى كتابة اسم واضح للأنشودة.")
        return

    status_message = await update.message.reply_text(f"🔍 جاري البحث عن: ({query})...")

    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, search_youtube_results, query)

        if not results:
            await status_message.edit_text("❌ لم يتم العثور على نتائج. جرب كتابة اسم الأنشودة بشكل صحيح.")
            return

        keyboard = []
        for idx, entry in enumerate(results):
            title = entry.get('title', f'نتيجة {idx+1}')
            short_title = title[:40] + "..." if len(title) > 40 else title
            video_url = entry.get('url') if entry.get('url') else f"https://youtube.com{entry.get('id')}"

            context.user_data[f"url_{idx}"] = video_url
            context.user_data[f"title_{idx}"] = title

            keyboard.append([InlineKeyboardButton(f"🎵 {short_title}", callback_data=f"select_{idx}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await status_message.delete()
        await update.message.reply_text("📌 اختر النتيجة الأقرب لطلبك:", reply_markup=reply_markup)

    except Exception as e:
        print(f"Search Error: {e}")
        await status_message.edit_text("❌ حدث خطأ أثناء البحث. جرب مجدداً.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("select_"):
        idx = data.split("_")[1]
        context.user_data["current_url"] = context.user_data.get(f"url_{idx}")
        context.user_data["current_title"] = context.user_data.get(f"title_{idx}")

        keyboard = [
            [
                InlineKeyboardButton("🎧 تحميل كصوت (MP3)", callback_data="download_audio"),
                InlineKeyboardButton("🎬 تحميل كفيديو (MP4)", callback_data="download_video")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=f"📋 الخيار المختار:\n*{context.user_data['current_title']}*\n\nاختر نوع التحميل:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    elif data in ["download_audio", "download_video"]:
        download_type = "audio" if data == "download_audio" else "video"
        url = context.user_data.get("current_url")
        title = context.user_data.get("current_title")

        await query.edit_message_text(text="⏳ جاري التحميل والمعالجة، يرجى الانتظار...")

        try:
            loop = asyncio.get_event_loop()
            media_path, final_title = await loop.run_in_executor(None, download_media, url, download_type)

            if os.path.exists(media_path):
                await query.edit_message_text(text="⚡ جاري الرفع المنظم إلى تيلجرام...")

                with open(media_path, 'rb') as file:
                    if download_type == "audio":
                        await query.message.reply_audio(audio=file, title=final_title, caption=f"🎧 {final_title}")
                    else:
                        await query.message.reply_video(video=file, caption=f"🎬 {final_title}")

                os.remove(media_path)
                await query.message.delete()
            else:
                await query.edit_message_text("❌ فشل معالجة الملف.")

        except Exception as e:
            print(f"Error: {e}")
            await query.edit_message_text("❌ حدث خطأ أثناء جلب الملف.")

def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == '__main__':
    main()
