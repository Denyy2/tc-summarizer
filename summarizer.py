"""OpenAI-backed summarization. Uses the current (v1+) OpenAI SDK — the
original prototype used the pre-1.0 `openai.ChatCompletion.create(...)`
style, which was removed when openai-python hit v1.0 in Nov 2023."""

from __future__ import annotations

import os

from openai import APIError, OpenAI, OpenAIError

# Configurable so the model can be swapped without a code change.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Keeps a single very long document from blowing the context window or
# running up an unbounded bill on one request.
MAX_INPUT_CHARS = 20_000

SYSTEM_PROMPT = (
    "You are a lawyer reviewing terms and conditions for a client. Summarize "
    "the document's key points and practical implications in plain English. "
    "Call out anything a typical user should be cautious about — data usage, "
    "liability limits, auto-renewal, arbitration clauses, and similar terms. "
    "Keep it concise and use short bullet points where useful."
)


class SummarizationError(Exception):
    """Raised when the summarization call fails or input is invalid."""


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SummarizationError(
            "OPENAI_API_KEY isn't set. Add it to your .env file (see .env.example)."
        )
    return OpenAI(api_key=api_key)


def summarize(text: str) -> str:
    text = text.strip()
    if not text:
        raise SummarizationError("No text to summarize.")

    truncated = text[:MAX_INPUT_CHARS]
    client = get_client()

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": truncated},
            ],
            max_tokens=700,
            temperature=0.3,
        )
    except (APIError, OpenAIError) as exc:
        raise SummarizationError(f"OpenAI request failed: {exc}") from exc

    summary = response.choices[0].message.content
    if not summary:
        raise SummarizationError("OpenAI returned an empty response.")
    return summary.strip()
