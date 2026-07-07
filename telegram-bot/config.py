"""
ملف إعدادات البوت. يقرأ القيم من متغيرات البيئة (Secrets) ويوفر
قيماً افتراضية معقولة للسلوك العام للبوت.
"""

import os

# توكن البوت من @BotFather - يجب ضبطه كـ Secret باسم TELEGRAM_BOT_TOKEN
BOT_TOKEN: str | None = os.environ.get("TELEGRAM_BOT_TOKEN")

# طريقة البحث في تيك توك عبر yt-dlp (أول نتيجة مطابقة)
TIKTOK_SEARCH_PREFIX = "tiktoksearch1"

# الحد الأقصى لحجم الملف الذي يمكن إرساله عبر بوتات تيلجرام العادية (بالبايت)
MAX_TELEGRAM_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# جودة الصوت المستخرج (kbps) عند تحويل الفيديو إلى mp3
AUDIO_QUALITY = "192"

# مستوى تسجيل السجلات (logging)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
