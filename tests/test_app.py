"""Route-level tests. The OpenAI call is monkeypatched so these run without
a real API key or network access; OCR/Tesseract isn't exercised here since
it's a system dependency this test environment may not have installed —
see extraction.py for the extraction logic itself.
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client


def test_index_ok(client):
    res = client.get("/")
    assert res.status_code == 200


def test_health_ok(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}


def test_summarize_rejects_empty_input(client):
    res = client.post("/summarize", data={"text": ""})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_summarize_rejects_unsupported_file_type(client):
    data = {"file": (io.BytesIO(b"not a real file"), "notes.txt")}
    res = client.post("/summarize", data=data, content_type="multipart/form-data")
    assert res.status_code == 400


def test_summarize_returns_summary_for_pasted_text(client, monkeypatch):
    monkeypatch.setattr(app_module, "summarize", lambda text: f"summary of: {text}")
    res = client.post("/summarize", data={"text": "Some terms and conditions."})
    assert res.status_code == 200
    body = res.get_json()
    assert body["summary"] == "summary of: Some terms and conditions."
    assert body["usedOcr"] is False
