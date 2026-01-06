from __future__ import annotations

import builtins
import importlib
import sys

from research_synth import chunking


def test_chunking_fallback_when_tiktoken_missing(monkeypatch):
    """Simulate that `tiktoken` is not available and assert chunking falls back to whitespace tokens."""
    # Replace import with a fake that raises ImportError for tiktoken
    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tiktoken" or name.startswith("tiktoken."):
            raise ImportError("No module named tiktoken")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Reload the chunking module so it re-evaluates the import attempt
    importlib.reload(sys.modules["research_synth.chunking"])  # reload in-place
    mod = sys.modules["research_synth.chunking"]

    # Confirm fallback flag is set
    assert getattr(mod, "_USE_TIKTOKEN", False) is False

    # Use a deterministic input to validate whitespace-based chunking
    text = "one two three four five six"
    chunks = mod.chunk_text(text, max_tokens=2, overlap=1)

    # Basic checks: chunk objects, expected splitting by words
    assert all(hasattr(c, "index") and hasattr(c, "text") for c in chunks)
    # Ensure at least one chunk contains the expected words
    assert any("one" in c.text for c in chunks)

    # Restore import behavior
    monkeypatch.setattr(builtins, "__import__", orig_import)