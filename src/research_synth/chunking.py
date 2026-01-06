from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import tiktoken

@dataclass(frozen=True)
class Chunk:
    index: int
    text: str

def chunk_text(text: str, max_tokens: int = 800, overlap: int = 100) -> list[Chunk]:
    # Token-aware chunking using tiktoken (fast, stable).
    text = (text or "").strip()
    if not text:
        return []

    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    if not tokens:
        return []

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens).strip()
        if chunk_text:
            chunks.append(Chunk(index=idx, text=chunk_text))
            idx += 1
        if end == len(tokens):
            break
        # overlap
        start = max(0, end - overlap)
    return chunks


from research_synth.tokenizer import get_token_counter, TokenizerInfo

def chunk_text_with_meta(text: str, *, max_tokens: int, overlap: int) -> tuple[list[str], TokenizerInfo]:
    count_tokens, info = get_token_counter()
    # If chunk_text supports count_tokens, use it; else fall back.
    if "chunk_text" in globals():
        try:
            chunks = chunk_text(text, max_tokens=max_tokens, overlap=overlap, count_tokens=count_tokens)  # type: ignore[arg-type]
            return chunks, info
        except TypeError:
            pass

    parts = [p.strip() for p in (text or "").split("\n\n") if p.strip()]
    out: list[str] = []
    buf = ""
    for p in parts:
        candidate = (buf + "\n\n" + p).strip() if buf else p
        if count_tokens(candidate) <= max_tokens:
            buf = candidate
            continue
        if buf:
            out.append(buf)
        buf = p
    if buf:
        out.append(buf)
    return out, info
