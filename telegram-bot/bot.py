import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

RESULTS_PER_PAGE = 5   # عدد النتائج في كل صفحة
TOTAL_RESULTS    = 20  # إجمالي النتائج التي يجلبها البوت

# ─────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 *بوت الأناشيد*\n\n"
        "أرسل اسم النشيد أو الأغنية وسأبحث لك عنها في يوتيوب.\n"
        "ستظهر لك النتائج على صفحات، تنقّل بينها واختر ما يناسبك.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🏴 *مَكْتَبَةُ الأَنَاشِيدِ الجِهَادِيَّةِ* 🏴\n\n"
        "\"إِنَّ مِنَ البَيَانِ لَسِحْراً، وَإِنَّ مِنَ الشِّعْرِ لَحِكْمَةً\"\n\n"
        "مرحباً بك في منبر الكلمة الصادقة واللحن الحادي. أرسل الآن *اسم الأنشودة*، "
        "لتبحر في مكتبة تجمع بين زئير الصوتيات وعز المرتجيات بصيغتي الصوت والفيديو.\n\n"
        "ーーー\n"
        "*وفي ظلال هذا الصرح، تحيةٌ معطرة بعبق المجد لأميرة البيت وعنوان الثبات: (الأندلسية)* 🪶\n\n"
        "هِيَ الأَنْدَلُسِيَّةُ فِي لَهِيبِ المَعَامِعِ المَجْدُ مَسْكَنُهَا\n"
        "سَلِيلَةُ عِزٍّ بِالعَقِيدَةِ وَالفِدَا تَسْمُو بِمَوْطِنِهَا\n\n"
        "خَاضَتْ فِجَاجَ الحَرْبِ ثَابِتَةَ الخُطَى لَا تَنْثَنِي\n"
        "زَوْجٌ كَمِثْلِ السَّيْفِ فِي كَفِّ الـمُجَاهِدِ مَعْدِنُهَا",
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────────
def search_youtube_results(query: str, count: int = TOTAL_RESULTS) -> list:
    """يجلب (count) نتيجة من يوتيوب للاستعلام المعطى."""
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'extract_flat': 'in_playlist',
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{count}:{query}", download=False)
        if info and 'entries' in info:
            return [e for e in info['entries'] if e]
    return []

# ─────────────────────────────────────────────
def build_results_keyboard(results: list, page: int) -> InlineKeyboardMarkup:
    """يبني لوحة المفاتيح لصفحة معينة من النتائج."""
    total_pages = max(1, (len(results) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE)
    start = page * RESULTS_PER_PAGE
    end   = start + RESULTS_PER_PAGE
    page_results = results[start:end]

    keyboard = []

    # أزرار النتائج
    for i, entry in enumerate(page_results):
        abs_idx   = start + i
        title     = entry.get('title') or f'نتيجة {abs_idx + 1}'
        short     = title[:45] + "…" if len(title) > 45 else title
        duration  = entry.get('duration')
        dur_str   = f"  [{int(duration//60)}:{int(duration%60):02d}]" if duration else ""
        keyboard.append([
            InlineKeyboardButton(f"🎵 {short}{dur_str}", callback_data=f"select_{abs_idx}")
        ])

    # أزرار التنقل بين الصفحات
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ السابق", callback_data=f"page_{page - 1}"))
    nav.append(InlineKeyboardButton(f"📄 {page + 1} / {total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("التالي ▶️", callback_data=f"page_{page + 1}"))
    keyboard.append(nav)

    return InlineKeyboardMarkup(keyboard)

# ─────────────────────────────────────────────
def results_header(query: str, page: int, total: int) -> str:
    total_pages = max(1, (total + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE)
    start = page * RESULTS_PER_PAGE + 1
    end   = min(start + RESULTS_PER_PAGE - 1, total)
    return (
        f"🔎 نتائج البحث عن: *{query}*\n"
        f"عرض {start}–{end} من أصل {total} نتيجة  |  صفحة {page + 1} من {total_pages}\n\n"
        "اختر النشيد الذي تريده:"
    )

# ─────────────────────────────────────────────
def download_media(url: str, download_type: str) -> tuple[str, str]:
    os.makedirs('downloads', exist_ok=True)
    if download_type == "audio":
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }
    else:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info     = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if download_type == "audio":
            filename = os.path.splitext(filename)[0] + ".mp3"
        return filename, info.get('title', 'نشيد')

# ─────────────────────────────────────────────
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if len(query) < 2:
        await update.message.reply_text("يرجى كتابة اسم واضح للأنشودة.")
        return

    status = await update.message.reply_text(f"🔍 جاري البحث عن: *{query}* …", parse_mode="Markdown")

    try:
        loop    = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, search_youtube_results, query, TOTAL_RESULTS)

        if not results:
            await status.edit_text("❌ لم أجد نتائج. جرّب كتابة الاسم بشكل مختلف.")
            return

        # حفظ النتائج ومعلومات الصفحة في بيانات المستخدم
        context.user_data['results'] = results
        context.user_data['query']   = query
        context.user_data['page']    = 0

        await status.edit_text(
            text         = results_header(query, 0, len(results)),
            reply_markup = build_results_keyboard(results, 0),
            parse_mode   = "Markdown"
        )

    except Exception as e:
        print(f"Search Error: {e}")
        await status.edit_text("❌ حدث خطأ أثناء البحث. جرّب مجدداً.")

# ─────────────────────────────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cb   = update.callback_query
    data = cb.data
    await cb.answer()

    # ── زر بلا وظيفة (مؤشر الصفحة) ──────────────────
    if data == "noop":
        return

    # ── التنقل بين الصفحات ───────────────────────────
    if data.startswith("page_"):
        page    = int(data.split("_")[1])
        results = context.user_data.get('results', [])
        query   = context.user_data.get('query', '')
        context.user_data['page'] = page

        await cb.edit_message_text(
            text         = results_header(query, page, len(results)),
            reply_markup = build_results_keyboard(results, page),
            parse_mode   = "Markdown"
        )
        return

    # ── اختيار نتيجة ─────────────────────────────────
    if data.startswith("select_"):
        idx     = int(data.split("_")[1])
        results = context.user_data.get('results', [])

        if idx >= len(results):
            await cb.edit_message_text("❌ انتهت صلاحية هذه النتيجة، ابحث مجدداً.")
            return

        entry = results[idx]
        url   = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
        title = entry.get('title', 'نشيد')

        context.user_data['current_url']   = url
        context.user_data['current_title'] = title

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎧 صوت (MP3)", callback_data="download_audio"),
            InlineKeyboardButton("🎬 فيديو (MP4)", callback_data="download_video"),
        ],[
            InlineKeyboardButton("🔙 العودة للنتائج", callback_data=f"page_{context.user_data.get('page', 0)}")
        ]])

        short = title[:60] + "…" if len(title) > 60 else title
        await cb.edit_message_text(
            text         = f"📋 *{short}*\n\nاختر نوع التحميل:",
            parse_mode   = "Markdown",
            reply_markup = keyboard
        )
        return

    # ── تحميل الملف ──────────────────────────────────
    if data in ("download_audio", "download_video"):
        download_type = "audio" if data == "download_audio" else "video"
        url           = context.user_data.get('current_url')
        title         = context.user_data.get('current_title', 'نشيد')

        if not url:
            await cb.edit_message_text("❌ انتهت صلاحية الجلسة، ابحث مجدداً.")
            return

        await cb.edit_message_text("⏳ جاري التحميل والمعالجة، يرجى الانتظار…")

        try:
            loop       = asyncio.get_event_loop()
            media_path, final_title = await loop.run_in_executor(
                None, download_media, url, download_type
            )

            if not os.path.exists(media_path):
                await cb.edit_message_text("❌ فشل معالجة الملف، جرّب مجدداً.")
                return

            file_size = os.path.getsize(media_path)
            if file_size > 50 * 1024 * 1024:
                os.remove(media_path)
                await cb.edit_message_text("⚠️ حجم الملف أكبر من 50MB وهو الحد الأقصى لتيلجرام.")
                return

            await cb.edit_message_text("⚡ جاري الرفع إلى تيلجرام…")

            with open(media_path, 'rb') as f:
                if download_type == "audio":
                    await cb.message.reply_audio(audio=f, title=final_title, caption=f"🎧 {final_title}")
                else:
                    await cb.message.reply_video(video=f, caption=f"🎬 {final_title}")

            os.remove(media_path)
            await cb.message.delete()

        except Exception as e:
            print(f"Download Error: {e}")
            await cb.edit_message_text("❌ حدث خطأ أثناء التحميل، جرّب مجدداً.")

# ─────────────────────────────────────────────
def main():
    os.makedirs('downloads', exist_ok=True)
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
