"""Read PDF, HTML or text into lines. PDF lines keep position and font size, which the legal parser
uses to tell body text from margin notes and to rebuild the Schedule table."""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


@dataclass
class Line:
    text: str
    page: int = 0
    x: float = 0.0
    y: float = 0.0
    size: float = 0.0  # 0 = unknown (plain text / HTML)
    font: str = ""


class _HTMLText(HTMLParser):
    _BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article"}
    _HEAD = {"h1", "h2", "h3", "h4"}

    def __init__(self):
        super().__init__()
        self.out: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer"):
            self._skip += 1
        elif tag in self._BLOCK:
            self.out.append("\n" + ("# " if tag in self._HEAD else ""))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer"):
            self._skip = max(0, self._skip - 1)
        elif tag in self._BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.out.append(data)


def _pdf_lines(path: Path) -> list[Line]:
    import pymupdf

    lines: list[Line] = []
    with pymupdf.open(path) as doc:
        for pno, page in enumerate(doc):
            for block in page.get_text("dict")["blocks"]:
                for ln in block.get("lines", []):
                    text = "".join(s["text"] for s in ln["spans"]).strip()
                    if text:
                        s0 = ln["spans"][0]
                        lines.append(Line(text, pno, ln["bbox"][0], ln["bbox"][1], s0["size"], s0["font"]))
    # Reading order by position: block order in gazette PDFs puts mastheads and table columns out of sequence.
    lines.sort(key=lambda l: (l.page, round(l.y), l.x))
    return lines


def read_lines(path: str | Path) -> list[Line]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pdf_lines(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    if suffix in (".html", ".htm"):
        parser = _HTMLText()
        parser.feed(text)
        text = "".join(parser.out)
    return [Line(t.strip(), y=float(i)) for i, t in enumerate(text.splitlines()) if t.strip()]


def read_text(path: str | Path) -> str:
    return "\n".join(l.text for l in read_lines(path))
