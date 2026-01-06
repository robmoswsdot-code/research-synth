from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class TokenizerInfo:
    name: str
    fidelity: str  # "high" or "low"
    detail: str

def get_token_counter() -> tuple[Callable[[str], int], TokenizerInfo]:
    """Return a token-count function and metadata."""
    try:
        import tiktoken  # type: ignore
    except Exception as e:  # noqa: BLE001
        def count_ws(text: str) -> int:
            return len((text or "").split())
        return count_ws, TokenizerInfo(
            name="whitespace",
            fidelity="low",
            detail=f"tiktoken unavailable: {e.__class__.__name__}",
        )

    enc = tiktoken.get_encoding("o200k_base")

    def count_tk(text: str) -> int:
        return len(enc.encode(text or ""))

    return count_tk, TokenizerInfo(
        name="tiktoken:o200k_base",
        fidelity="high",
        detail="ok",
    )
