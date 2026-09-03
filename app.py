import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from extraction import ExtractionError, extract_text
from summarizer import SummarizationError, summarize

load_dotenv()

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB upload cap

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


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
def summarize_route():
    uploaded = request.files.get("file")

    try:
        if uploaded and uploaded.filename:
            _, ext = os.path.splitext(uploaded.filename.lower())
            if ext not in ALLOWED_EXTENSIONS:
                return jsonify({"error": f"Unsupported file type: {ext or 'unknown'}"}), 400

            text, used_ocr = extract_text(uploaded.filename, uploaded.read())
            summary = summarize(text)
            return jsonify({"summary": summary, "usedOcr": used_ocr, "extractedChars": len(text)})

        text = (request.form.get("text") or "").strip()
        if not text:
            return jsonify({"error": "Paste some text or upload a PDF/image."}), 400

        summary = summarize(text)
        return jsonify({"summary": summary, "usedOcr": False, "extractedChars": len(text)})

    except ExtractionError as exc:
        return jsonify({"error": str(exc)}), 422
    except SummarizationError as exc:
        return jsonify({"error": str(exc)}), 502


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, port=int(os.getenv("PORT", 5000)))
