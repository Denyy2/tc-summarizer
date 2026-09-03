# Terms & Conditions Summarizer

Paste dense legal text — or upload a PDF or scanned image — and get a plain-English summary
of the key points and what to watch out for, powered by the OpenAI API.

## How extraction works

- **Pasted text** goes straight to the summarizer.
- **PDFs** are read directly page-by-page first (fast, exact, free). A page that yields little
  or no extractable text is assumed to be a scan and is rendered to an image and run through
  OCR instead — so both "real" text PDFs and scanned PDFs work through the same endpoint.
- **Images** (PNG/JPEG) always go through OCR.

PDF rendering uses [PyMuPDF](https://pymupdf.readthedocs.io/), which needs no external binary.
OCR uses [Tesseract](https://github.com/tesseract-ocr/tesseract) via `pytesseract` — that's the
one system dependency this project needs beyond Python packages.

## Stack

Flask · OpenAI API (`gpt-4o-mini` by default, configurable) · PyMuPDF · Tesseract OCR ·
vanilla HTML/CSS/JS frontend

## Local setup

Requires Python 3.12+ and [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) installed
and on your `PATH` (for the OCR fallback — the app still runs without it for pasted text and
text-based PDFs, but scanned documents will error).

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements-dev.txt
cp .env.example .env         # then add your OPENAI_API_KEY
python app.py
```

Open [http://localhost:5000](http://localhost:5000).

## Tests

```bash
pytest
```

Route/validation tests run without a real API key (the OpenAI call is mocked). OCR itself isn't
covered by these tests since it depends on Tesseract being installed in the test environment.

## Deployment

Ships with a `Dockerfile` that installs Tesseract as part of the image, so any Docker-based host
(Render, Railway, Fly.io, etc.) works without extra setup. Set `OPENAI_API_KEY` as an environment
variable on the host; `PORT` is provided automatically by most platforms.
