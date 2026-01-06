from __future__ import annotations

from pathlib import Path

def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text()

def extract_txt(path: Path) -> list[tuple[str, str]]:
    return [("TXT", read_text_file(path))]

def extract_md(path: Path) -> list[tuple[str, str]]:
    # v0.1: treat Markdown as plain text (fast, reliable)
    return [("MD", read_text_file(path))]

def extract_docx(path: Path) -> list[tuple[str, str]]:
    try:
        from docx import Document
    except ModuleNotFoundError as e:
        raise RuntimeError("DOCX support not installed. Run: pip install -e '.[docx]'") from e

    doc = Document(str(path))
    parts = []
    for para in doc.paragraphs:
        t = (para.text or "").strip()
        if t:
            parts.append(t)
    return [("DOCX", "\n".join(parts))]

def extract_pdf(path: Path) -> list[tuple[str, str]]:
    try:
        import fitz  # PyMuPDF
    except ModuleNotFoundError as e:
        raise RuntimeError("PDF support not installed. Run: pip install -e '.[pdf]'") from e

    doc = fitz.open(str(path))
    out: list[tuple[str, str]] = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = (page.get_text("text") or "").strip()
        if text:
            out.append((f"Page {i+1}", text))
    return out or [("PDF", "")]

def extract_excel(path: Path) -> list[tuple[str, str]]:
    try:
        import pandas as pd
    except ModuleNotFoundError as e:
        raise RuntimeError("Excel support not installed. Run: pip install -e '.[excel]'") from e

    out: list[tuple[str, str]] = []
    xls = pd.ExcelFile(str(path))
    for sheet in xls.sheet_names:
        df = xls.parse(sheet_name=sheet, dtype=str)
        text = df.fillna("").to_csv(index=False).strip()
        if text:
            out.append((f"Sheet {sheet}", text))
    return out or [("EXCEL", "")]

def extract_file(path: Path) -> list[tuple[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return extract_txt(path)
    if suffix == ".md":
        return extract_md(path)
    if suffix == ".docx":
        return extract_docx(path)
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix in [".xlsx", ".xlsm", ".xls"]:
        return extract_excel(path)
    return []
