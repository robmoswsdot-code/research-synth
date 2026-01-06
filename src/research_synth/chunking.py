from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

try:
    import tiktoken
    _USE_TIKTOKEN = True
except Exception:
    _USE_TIKTOKEN = False

@dataclass(frozen=True)
class Chunk:
    index: int
    text: str

def chunk_text(text: str, max_tokens: int = 800, overlap: int = 100) -> list[Chunk]:
    # Token-aware chunking using tiktoken when available; falls back to whitespace tokens.
    text = (text or "").strip()
    if not text:
        return []

    if _USE_TIKTOKEN:
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)
        if not tokens:
            return []
        def _decode(toklist):
            return enc.decode(toklist)
    else:
        # Simple fallback tokenizer: split on whitespace and treat words as tokens.
        tokens = text.split()
        if not tokens:
            return []
        def _decode(toklist):
            return " ".join(toklist)

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = _decode(chunk_tokens).strip()
        if chunk_text:
            chunks.append(Chunk(index=idx, text=chunk_text))
            idx += 1
        if end == len(tokens):
            break
        # overlap
        start = max(0, end - overlap)
    return chunks
