from pathlib import Path

from pypdf import PdfReader

SUPPORTED = {".pdf", ".txt", ".md"}


def load_document(path: Path) -> list[dict]:
    """Return [{'page': n, 'text': str}] (1-based pages)."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        reader = PdfReader(str(path))
        pages = []
        for i, p in enumerate(reader.pages):
            try:  # keeps table rows
                text = p.extract_text(extraction_mode="layout")
            except Exception:
                text = p.extract_text()
            pages.append({"page": i + 1, "text": text or ""})
        return pages
    if ext in {".txt", ".md"}:
        return [{"page": 1, "text": path.read_text(encoding="utf-8", errors="ignore")}]
    raise ValueError(f"Unsupported file type: {ext}")
