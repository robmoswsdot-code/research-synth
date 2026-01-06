from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Optional

API_URL = "https://api.openai.com/v1/responses"

@dataclass(frozen=True)
class OpenAIResponse:
    raw: dict[str, Any]

    def extract_text(self) -> str:
        # Prefer explicit field if present (some SDKs expose this helper)
        if isinstance(self.raw.get("output_text"), str) and self.raw["output_text"].strip():
            return self.raw["output_text"]

        # Otherwise, walk output items and gather text-ish fields
        out = []
        for item in self.raw.get("output", []) or []:
            content = item.get("content") or []
            for c in content:
                if c.get("type") in ("output_text", "text") and isinstance(c.get("text"), str):
                    out.append(c["text"])
        return "\n".join(out).strip()

def responses_create(
    *,
    api_key: str,
    model: str,
    input_items: list[dict[str, Any]],
    text_format: Optional[dict[str, Any]] = None,
    timeout_s: int = 120,
) -> OpenAIResponse:
    body: dict[str, Any] = {
        "model": model,
        "input": input_items,
    }
    if text_format is not None:
        # Responses API expects: text: { format: { ... } }
        body["text"] = {"format": text_format}

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
        raise RuntimeError(f"OpenAI API HTTPError {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"OpenAI API URLError: {e}") from e

    raw = json.loads(payload)
    return OpenAIResponse(raw=raw)
