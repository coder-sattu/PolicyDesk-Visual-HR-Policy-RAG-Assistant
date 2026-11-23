import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

HEADING = re.compile(r"^(\d{1,2}\.\s+[A-Z][^\n]{2,80})$", re.M)


def chunk_pages(pages: list[dict], size: int, overlap: int) -> list[dict]:
    """Split page text into overlapping chunks, tracking page and section."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=size, chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""])
    chunks, section = [], None
    for p in pages:
        text = p["text"]
        heads = [(m.start(), m.group(1).strip()) for m in HEADING.finditer(text)]
        cursor = 0
        for piece in splitter.split_text(text):
            pos = text.find(piece[:40], cursor)
            pos = cursor if pos < 0 else pos
            cursor = pos
            # heading at chunk start
            for start, h in heads:
                if start <= pos + 5:
                    section = h
            chunks.append({
                "chunk_index": len(chunks), "page": p["page"], "section": section,
                "text": piece, "chars": len(piece),
            })
    return chunks
