from __future__ import annotations

from pathlib import Path
from diskcache import Cache

def open_cache(cache_dir: Path) -> Cache:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return Cache(str(cache_dir))
