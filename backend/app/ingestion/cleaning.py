import re
from collections import Counter

PAGE_LABEL = re.compile(r"^\s*page\s*\d+(\s*(of|/)\s*\d+)?\s*$", re.I)
BARE_NUM = re.compile(r"^\s*\d{1,4}\s*$")
HEADING = re.compile(r"^\d{1,2}\.\s+[A-Z][^.]{2,80}$")
GAP = re.compile(r" {3,}")


def _parts(line: str) -> list[str]:
    return [re.sub(r"\s+", " ", p).strip() for p in GAP.split(line.strip()) if p.strip()]


def clean_pages(pages: list[dict]) -> tuple[list[dict], dict]:
    """Strip repeated headers/footers and page numbers, keep table rows, fix wraps."""
    part_sets = [set(x for l in p["text"].splitlines() for x in _parts(l)) for p in pages]
    counts = Counter(x for s in part_sets for x in s)
    min_repeat = max(2, int(len(pages) * 0.6))
    boilerplate = {x for x, c in counts.items()
                   if len(pages) > 1 and c >= min_repeat and not BARE_NUM.match(x)}

    removed, cleaned, table_rows = [], [], 0
    chars_before = sum(len(p["text"]) for p in pages)
    for p in pages:
        raw = p["text"].splitlines()
        nonempty = [i for i, l in enumerate(raw) if l.strip()]
        edges = {nonempty[0], nonempty[-1]} if nonempty else set()
        out: list[str] = []
        for i, line in enumerate(raw):
            parts = _parts(line)
            if not parts:
                if out and out[-1] != "":
                    out.append("")  # paragraph break
                continue
            keep = []
            for x in parts:
                # page numbers only at edges
                if x in boilerplate or PAGE_LABEL.match(x) or (i in edges and BARE_NUM.match(x)):
                    removed.append(x)
                else:
                    keep.append(x)
            if not keep:
                continue
            if len(keep) > 1:  # table row
                out.append(" | ".join(keep))
                table_rows += 1
                continue
            s, prev = keep[0], (out[-1] if out else "")
            if prev and "|" not in prev and not HEADING.match(prev) and not HEADING.match(s):
                out[-1] = (prev[:-1] + s) if prev.endswith("-") else f"{prev} {s}"  # soft wrap
            else:
                out.append(s)
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
        if text:
            cleaned.append({"page": p["page"], "text": text})

    stats = {
        "chars_before": chars_before,
        "chars_after": sum(len(p["text"]) for p in cleaned),
        "removed_lines": len(removed),
        "removed_examples": sorted(set(removed))[:5],
        "table_rows_detected": table_rows,
        "empty_pages_dropped": len(pages) - len(cleaned),
    }
    return cleaned, stats
