from __future__ import annotations

import json
import types
import urllib.request
from research_synth.openai_http import responses_create

class DummyResp:
    def __init__(self, payload: dict):
        self._b = json.dumps(payload).encode("utf-8")
    def read(self):
        return self._b
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False

def test_openai_http_extracts_text(monkeypatch):
    payload = {
        "id": "resp_test",
        "output": [
            {"type":"message","content":[{"type":"output_text","text":"{\"concepts\":[{\"label\":\"x\",\"category\":\"finding\",\"summary\":\"s\",\"confidence\":\"low\",\"evidence\":[]}]}"}]}
        ]
    }

    def fake_urlopen(req, timeout=0):
        return DummyResp(payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    r = responses_create(
        api_key="test",
        model="gpt-4o-mini",
        input_items=[{"role":"user","content":"hi"}],
        text_format={"type":"json_schema","strict":True,"schema":{"type":"object","properties":{"concepts":{"type":"array"}},"required":["concepts"]}},
    )
    assert "{\"concepts\"" in r.extract_text()
