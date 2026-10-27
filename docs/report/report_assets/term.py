"""Renders captured command output as a terminal-window image (for the Testing chapter)."""
import pathlib, sys
from PIL import Image, ImageDraw, ImageFont


def render(text, out, title="Terminal", width_chars=110):
    font = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 26)
    bold = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 26)
    lines = []
    for raw in text.rstrip().splitlines():
        while len(raw) > width_chars:
            lines.append(raw[:width_chars]); raw = "    " + raw[width_chars:]
        lines.append(raw)
    lh = 34; pad = 28; bar = 54
    W = pad * 2 + int(font.getlength("M") * width_chars); H = bar + pad * 2 + lh * len(lines)
    im = Image.new("RGB", (W, H), "#0C0C0C"); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, bar], fill="#1F1F1F")
    for i, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")): d.ellipse([20 + i * 34, 17, 40 + i * 34, 37], fill=c)
    d.text((140, 13), title, font=font, fill="#BBBBBB")
    for i, ln in enumerate(lines):
        col = "#D4D4D4"; f = font
        if "passed" in ln or ln.startswith("ok") or "PASSED" in ln: col = "#6CD07A"
        if "failed" in ln.lower() or "error" in ln.lower(): col = "#F27878"
        if ln.startswith("$") or ln.startswith("PS "): col = "#7FB7FF"; f = bold
        d.text((pad, bar + pad + i * lh), ln, font=f, fill=col)
    im.save(out)


if __name__ == "__main__":
    src, out, title = sys.argv[1], sys.argv[2], sys.argv[3]
    render(pathlib.Path(src).read_text(encoding="utf-8", errors="replace"), out, title)
