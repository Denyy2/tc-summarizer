"""Gemini-backed summarization.

Uses Google's free-tier Gemini API instead of a paid provider — the
original prototype (and an earlier revision of this file) used OpenAI,
which has no ongoing free tier and can silently run out of credits.
Get a free key with no credit card at https://aistudio.google.com/apikey.
"""

from __future__ import annotations

import os

from google import genai
from google.genai import types
from google.genai.errors import APIError

# Configurable so the model can be swapped without a code change.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

# Keeps a single very long document from blowing the context window or
# eating an outsized share of the daily free quota on one request.
MAX_INPUT_CHARS = 20_000
MAX_OUTPUT_TOKENS = 700

# gemini-flash-lite-latest was picked specifically for latency: the
# non-lite gemini-3.6-flash took 60-90s per request in testing (it spends
# an uncontrollable chunk of its output-token budget on internal "thinking"
# — it rejects thinking_budget=0, unlike older 2.5-series models) versus
# ~1s for the lite variant with equally usable summaries. If you swap models
# via GEMINI_MODEL, re-check latency before assuming it's still fast.

SYSTEM_PROMPT = (
    "You are a lawyer reviewing terms and conditions for a client. Summarize "
    "the document's key points and practical implications in plain English. "
    "Call out anything a typical user should be cautious about — data usage, "
    "liability limits, auto-renewal, arbitration clauses, and similar terms. "
    "Keep it concise and use short bullet points where useful."
)

_client: genai.Client | None = None


class SummarizationError(Exception):
    """Raised when the summarization call fails or input is invalid."""


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise SummarizationError(
                "GEMINI_API_KEY isn't set. Add it to your .env file (see .env.example) — "
                "get a free key at https://aistudio.google.com/apikey."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def summarize(text: str) -> str:
    text = text.strip()
    if not text:
        raise SummarizationError("No text to summarize.")

    truncated = text[:MAX_INPUT_CHARS]
    client = get_client()

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=truncated,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.3,
            ),
        )
    except APIError as exc:
        raise SummarizationError(f"Gemini request failed: {exc}") from exc

    summary = response.text
    if not summary:
        raise SummarizationError("Gemini returned an empty response.")
    return summary.strip()
