FROM python:3.12-slim

# تثبيت ffmpeg (مطلوب لاستخراج الصوت)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# نسخ ملفات المتطلبات أولاً للاستفادة من Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي الملفات
COPY bot.py config.py ./

# مجلد مؤقت للتنزيلات
RUN mkdir -p downloads

CMD ["python", "bot.py"]
