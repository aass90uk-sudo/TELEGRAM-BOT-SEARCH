"""
بوت تيلجرام لاستخراج الملفات الصوتية والمرئية من تيك توك.
المستخدم يكتب اسم الأغنية/النشيد، والبوت يبحث في تيك توك ويرسل له
الفيديو والصوت المستخرج منه.
"""

import logging
import os
import tempfile
import shutil
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import yt_dlp

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# نخزن نتائج البحث الأخيرة لكل مستخدم حتى يختار الصيغة (صوت/فيديو)
SEARCH_CACHE: dict[int, dict] = {}

MAX_TELEGRAM_FILE_SIZE = 50 * 1024 * 1024  # 50MB - حد بوتات تيلجرام العادية


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "أهلاً بك! 👋\n\n"
        "أرسل لي اسم الأغنية أو النشيد الذي تريده، وسأبحث لك عنه في تيك توك "
        "وأرسل لك الفيديو أو الصوت المستخرج منه.\n\n"
        "مثال: أرسل فقط اسم النشيد بدون أي شيء آخر."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "طريقة الاستخدام:\n"
        "1. اكتب اسم الأغنية أو النشيد.\n"
        "2. سيبحث البوت في تيك توك ويعرض لك أفضل نتيجة.\n"
        "3. اختر إن كنت تريد الفيديو أو الصوت فقط."
    )


def search_tiktok(query: str) -> dict | None:
    """يبحث في تيك توك عن أول نتيجة مطابقة للاستعلام ويعيد معلوماتها."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "default_search": "tiktoksearch1",
        "noplaylist": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if not info:
            return None
        if "entries" in info:
            entries = [e for e in info["entries"] if e]
            if not entries:
                return None
            return entries[0]
        return info


def download_media(url: str, want_audio: bool, out_dir: str) -> str | None:
    """يحمّل الفيديو أو يستخرج الصوت منه ويعيد مسار الملف الناتج."""
    out_template = str(Path(out_dir) / "%(id)s.%(ext)s")

    if want_audio:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "outtmpl": out_template,
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
    else:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "outtmpl": out_template,
            "format": "mp4/bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if want_audio:
            filename = str(Path(filename).with_suffix(".mp3"))
        if os.path.exists(filename):
            return filename
    return None


async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = (update.message.text or "").strip()
    if not query:
        return

    user_id = update.effective_user.id
    status_msg = await update.message.reply_text(f"🔎 جاري البحث عن: {query} ...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        result = search_tiktok(query)
    except Exception:
        logger.exception("فشل البحث في تيك توك")
        result = None

    if not result:
        await status_msg.edit_text(
            "لم أجد أي نتيجة لهذا الاسم على تيك توك. حاول بكتابة اسم آخر أو أدق."
        )
        return

    title = result.get("title") or result.get("description") or query
    url = result.get("webpage_url") or result.get("url")
    if not url:
        await status_msg.edit_text("حدث خطأ أثناء جلب رابط النتيجة، حاول مرة أخرى.")
        return

    SEARCH_CACHE[user_id] = {"url": url, "title": title}

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎬 فيديو", callback_data="video"),
                InlineKeyboardButton("🎵 صوت فقط", callback_data="audio"),
            ]
        ]
    )
    await status_msg.edit_text(
        f"وجدت هذه النتيجة:\n\n📌 {title}\n\nما الذي تريد إرساله؟",
        reply_markup=keyboard,
    )


async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query_cb = update.callback_query
    await query_cb.answer()

    user_id = update.effective_user.id
    data = SEARCH_CACHE.get(user_id)
    if not data:
        await query_cb.edit_message_text("انتهت صلاحية هذه النتيجة، أرسل اسم النشيد من جديد من فضلك.")
        return

    want_audio = query_cb.data == "audio"
    await query_cb.edit_message_text(
        f"⏳ جاري تحضير الـ{'صوت' if want_audio else 'فيديو'}، يرجى الانتظار..."
    )

    tmp_dir = tempfile.mkdtemp(prefix="tiktok_")
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.RECORD_VOICE if want_audio else ChatAction.UPLOAD_VIDEO,
        )
        file_path = download_media(data["url"], want_audio, tmp_dir)

        if not file_path or not os.path.exists(file_path):
            await query_cb.message.reply_text("تعذر تحميل الملف، حاول مرة أخرى.")
            return

        if os.path.getsize(file_path) > MAX_TELEGRAM_FILE_SIZE:
            await query_cb.message.reply_text(
                "حجم الملف أكبر من الحد المسموح به للإرسال عبر البوت."
            )
            return

        caption = data.get("title") or ""
        with open(file_path, "rb") as f:
            if want_audio:
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id, audio=f, caption=caption
                )
            else:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id, video=f, caption=caption
                )
    except Exception:
        logger.exception("فشل تحميل/إرسال الملف")
        await query_cb.message.reply_text("حدث خطأ غير متوقع أثناء المعالجة، حاول مرة أخرى.")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("متغير البيئة TELEGRAM_BOT_TOKEN غير موجود.")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_choice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))

    logger.info("البوت يعمل الآن...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
