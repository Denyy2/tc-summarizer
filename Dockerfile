FROM python:3.12-slim

# Tesseract is the OCR engine pytesseract wraps. PyMuPDF needs no extra
# system packages, which is why it's used instead of pdf2image (poppler).
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5000
EXPOSE 5000

# A single worker is intentional: the daily usage cap in usage_limit.py is
# an in-memory, per-process counter. Multiple workers would each keep their
# own count, silently multiplying the effective daily limit. Fine for a
# low-traffic portfolio demo; swap to a shared store (e.g. Redis) first if
# this ever needs real concurrency.
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 app:app
