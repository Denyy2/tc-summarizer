import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from extraction import ExtractionError, extract_text
from summarizer import SummarizationError, summarize
from usage_limit import DailyLimiter

load_dotenv()

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB upload cap

# Per-IP limit — stops one visitor from spamming the shared demo key.
PER_IP_LIMIT = os.getenv("PER_IP_RATE_LIMIT", "10 per 10 minutes")
# Global limit across every visitor combined — a hard ceiling that keeps
# the whole demo comfortably under the free-tier daily quota regardless
# of how many different people try it. See usage_limit.py.
DAILY_LIMIT = int(os.getenv("DAILY_SUMMARY_LIMIT", "150"))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

limiter = Limiter(get_remote_address, app=app, storage_uri="memory://", default_limits=[])
daily_limiter = DailyLimiter(DAILY_LIMIT)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/samples")
def samples():
    """Lets the UI offer a couple of one-click example documents."""
    result = []
    if os.path.isdir(SAMPLES_DIR):
        for name in sorted(os.listdir(SAMPLES_DIR)):
            path = os.path.join(SAMPLES_DIR, name)
            if os.path.isfile(path) and name.endswith(".txt"):
                with open(path, encoding="utf-8") as f:
                    result.append({"name": name, "text": f.read()})
    return jsonify(result)


@app.route("/summarize", methods=["POST"])
@limiter.limit(PER_IP_LIMIT)
def summarize_route():
    uploaded = request.files.get("file")

    try:
        if uploaded and uploaded.filename:
            _, ext = os.path.splitext(uploaded.filename.lower())
            if ext not in ALLOWED_EXTENSIONS:
                return jsonify({"error": f"Unsupported file type: {ext or 'unknown'}"}), 400
            text, used_ocr = extract_text(uploaded.filename, uploaded.read())
        else:
            text = (request.form.get("text") or "").strip()
            if not text:
                return jsonify({"error": "Paste some text or upload a PDF/image."}), 400
            used_ocr = False

        # Only an attempted model call counts against the shared daily quota —
        # checked here, after input validation/extraction, not before.
        if not daily_limiter.try_consume():
            return jsonify({"error": "Demo limit reached for today — please try again tomorrow."}), 429

        summary = summarize(text)
        return jsonify({
            "summary": summary,
            "usedOcr": used_ocr,
            "extractedChars": len(text),
            "remainingToday": daily_limiter.remaining,
        })

    except ExtractionError as exc:
        return jsonify({"error": str(exc)}), 422
    except SummarizationError as exc:
        return jsonify({"error": str(exc)}), 502


@app.errorhandler(429)
def rate_limited(_exc):
    return jsonify({"error": "Too many requests — please wait a bit and try again."}), 429


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, port=int(os.getenv("PORT", 5000)))
