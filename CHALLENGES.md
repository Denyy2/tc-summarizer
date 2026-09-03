# Challenges

Real problems hit building this, and how they got solved.

## 1. The default model was unusably slow

**Problem:** The first working version used `gemini-3.6-flash`, which took **60–90 seconds**
per request in testing. That's an unacceptable wait for a live demo, and long enough to exceed
a typical server's default request timeout (gunicorn defaults to 30s; this app's is set to 120s
specifically because of this issue).

**Diagnosis:** Rather than guess, each piece of the request config was tested in isolation
(system instruction, `max_output_tokens`, `temperature`, `thinking_config`) against the live API
to find which one was responsible. `thinking_budget=0` — the obvious fix, since disabling the
model's internal "thinking" step should cut latency — turned out to return `400 INVALID_ARGUMENT`
on this model. It doesn't support fully disabling thinking, unlike older Gemini 2.5-series models.

**Solution:** Queried the API directly for every model available to the key
(`client.models.list()`) instead of guessing model names from memory, and found
`gemini-flash-lite-latest` — a lighter, always-current alias. Same summarization quality,
**1–20 seconds** per request instead of 60–90.

## 2. A shared free-tier key behind a public URL

**Problem:** This is a public demo backed by one API key. A single heavy user — or a bot —
hitting `/summarize` repeatedly could burn through the entire daily free-tier quota, breaking
the demo for everyone else for the rest of the day.

**Solution:** Two rate-limit layers, both server-side so they can't be bypassed client-side:

- **Per-IP**: 10 requests / 10 minutes, via `Flask-Limiter`.
- **Global daily cap**: 150 requests/day across *every* visitor combined, enforced in
  `usage_limit.py`, and counted only *after* input validation — so a malformed request or an
  unsupported file type doesn't burn quota before ever reaching the model.

Verified live, not just in unit tests: fired 11 rapid requests at the running server and
confirmed the 10th succeeded and the 11th returned a real `429`.

One deliberate tradeoff: both limiters are in-memory and per-process, which is why the
Dockerfile runs a single gunicorn worker — multiple workers would each keep their own count,
silently multiplying the effective limit.

## 3. Supporting both real and scanned PDFs without a heavy dependency chain

**Problem:** Some uploaded PDFs have real, extractable text; others are scans with no text
layer at all and need OCR. The obvious approach (`pdf2image` to rasterize pages, then OCR)
needs Poppler as a second system dependency on top of Tesseract — more to install, more that
can break in a container build.

**Solution:** Used PyMuPDF for both jobs instead of two separate libraries: try direct text
extraction per page first (fast, exact, free), and only render+OCR a page if it yields close to
no text — a strong signal it's a scan, not a text PDF. PyMuPDF needs no external binary for
either job, so the Docker image only needs one extra system package (`tesseract-ocr`), not two.
