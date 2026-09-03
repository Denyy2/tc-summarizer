"""Text extraction for uploaded documents.

Strategy:
  - PDFs: try direct text extraction first (fast, exact, free). If a PDF has
    little/no extractable text — i.e. it's a scan, not a "real" text PDF —
    fall back to rendering each page as an image and running OCR on it.
  - Images (PNG/JPEG): OCR directly.

PyMuPDF handles both PDF text extraction and page rendering with no
external binary required. Only the OCR fallback needs a system dependency:
the Tesseract engine that `pytesseract` wraps.
"""

from __future__ import annotations

import io

import pymupdf
import pytesseract
from PIL import Image

# A PDF page that yields fewer than this many characters of direct text is
# treated as image-only (scanned) and routed through OCR instead.
MIN_DIRECT_TEXT_CHARS = 20

# Rendering PDF pages at this zoom level (~2x) keeps OCR accuracy reasonable
# without generating huge images for long documents.
PDF_RENDER_ZOOM = 2.0


class ExtractionError(Exception):
    """Raised when text can't be extracted from an uploaded file."""


def extract_text_from_pdf(file_bytes: bytes) -> tuple[str, bool]:
    """Returns (text, used_ocr). Tries direct extraction per page, falls
    back to OCR only for pages that don't yield real text."""
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    pages: list[str] = []
    used_ocr = False

    try:
        for page in doc:
            direct = page.get_text().strip()
            if len(direct) >= MIN_DIRECT_TEXT_CHARS:
                pages.append(direct)
                continue

            # Likely a scanned page — render it and OCR the image.
            used_ocr = True
            pix = page.get_pixmap(matrix=pymupdf.Matrix(PDF_RENDER_ZOOM, PDF_RENDER_ZOOM))
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            pages.append(pytesseract.image_to_string(image).strip())
    finally:
        doc.close()

    text = "\n\n".join(p for p in pages if p)
    if not text.strip():
        raise ExtractionError("No readable text found in this PDF.")
    return text, used_ocr


def extract_text_from_image(file_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(file_bytes))
    text = pytesseract.image_to_string(image).strip()
    if not text:
        raise ExtractionError("No readable text found in this image.")
    return text


def extract_text(filename: str, file_bytes: bytes) -> tuple[str, bool]:
    """Dispatches by file extension. Returns (text, used_ocr)."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    if lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return extract_text_from_image(file_bytes), True
    raise ExtractionError(f"Unsupported file type: {filename}")
