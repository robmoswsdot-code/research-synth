from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field
import yaml

class ResearchConfig(BaseModel):
    project_name: str = Field(default="Untitled Research Project")
    source_dirs: list[str] = Field(default_factory=lambda: ["sources"])
    output_format: str = Field(default="markdown")  # markdown | json (future)
    citation_style: str = Field(default="inline")   # inline | footnote (future)

def load_config(path: Path) -> ResearchConfig:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return ResearchConfig(**data)

def write_default_config(path: Path, project_name: str) -> None:
    cfg = ResearchConfig(project_name=project_name)
    path.write_text(
        yaml.safe_dump(cfg.model_dump(), sort_keys=False),
        encoding="utf-8",
    )
