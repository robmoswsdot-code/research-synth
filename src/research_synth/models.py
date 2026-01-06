from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal

class SourceChunk(BaseModel):
    chunk_id: str
    source_file: str
    location: str
    text: str
    hash: str  # file hash (sha256 of bytes)

class EvidenceRef(BaseModel):
    chunk_id: str
    source_file: str
    location: str
    quote: str | None = None

class ExtractedConcept(BaseModel):
    concept_id: str
    label: str
    category: Literal["finding","risk","recommendation","context","assumption"]
    summary: str
    confidence: Literal["low","medium","high"] = "medium"
    evidence: list[EvidenceRef] = Field(default_factory=list)
