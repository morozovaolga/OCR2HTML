import argparse
import json
import re
from pathlib import Path

import fitz  # PyMuPDF


def collect_block_text(block) -> str:
    lines = block.get("lines", [])
    # Concatenate spans per line, then join lines with \n
    line_texts = []
    for ln in lines:
        spans = ln.get("spans", [])
        txt = "".join(sp.get("text", "") for sp in spans)
        line_texts.append(txt)
    text = "\n".join(line_texts)
    # Normalize newlines and dehyphenate line-wrapped words within block
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove hyphen at line end if next line continues the word
    text = re.sub(r"(\w)[\-‑–—]\n(?=\w)", r"\1", text)
    # Merge single newlines inside block into spaces, keep paragraph feel per block
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    # Collapse spaces
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def page_blocks_with_roles(page):
    d = page.get_text("dict")
    blocks = []
    sizes = []
    for b in d.get("blocks", []):
        if b.get("type", 0) != 0:
            continue
        text = collect_block_text(b)
        if not text:
            continue
        # Weighted average font size by span char count
        lines = b.get("lines", [])
        total_chars = 0
        wsum = 0.0
        for ln in lines:
            for sp in ln.get("spans", []):
                s = sp.get("size", 0)
                t = sp.get("text", "") or ""
                n = len(t)
                if n and s:
                    wsum += s * n
                    total_chars += n
        if total_chars == 0:
            continue
        wsize = wsum / total_chars
        sizes.append(wsize)
        blocks.append({
            "bbox": b.get("bbox", [0, 0, 0, 0]),
            "text": text,
            "wsize": wsize,
            "line_count": len(lines),
            "chars": total_chars,
        })
    # Determine heading threshold per page
    if blocks:
        sizes_sorted = sorted(b["wsize"] for b in blocks)
        med = sizes_sorted[len(sizes_sorted)//2]
        thr = med * 1.35 + 0.5
    else:
        thr = 0

    pw = page.rect.width
    # Classify roles
    for b in blocks:
        x0, y0, x1, y1 = b["bbox"]
        cx = (x0 + x1) / 2
        centered = abs(cx - pw / 2) < pw * 0.12
        wide = (x1 - x0) > pw * 0.45
        short = b["line_count"] <= 3 and b["chars"] <= 200
        big_font = b["wsize"] >= thr
        is_heading = False
        if big_font and short:
            is_heading = True
        elif centered and short and not wide:
            is_heading = True
        b["role"] = "heading" if is_heading else "paragraph"
    # Sort by reading order (top, then left)
    blocks.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))
    return blocks


def to_html(blocks, title: str) -> str:
    from html import escape as esc
    body = []
    for blk in blocks:
        text = esc(blk["text"]) if blk["text"] else ""
        if blk["role"] == "heading":
            body.append(f"<h2>{text}</h2>")
        else:
            body.append(f"<p>{text}</p>")
    return (
        "<!doctype html>\n<html lang=\"ru\">\n<head>\n"
        "<meta charset=\"utf-8\"/>\n"
        f"<title>{esc(title)}</title>\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/>\n"
        "<style>body{font:18px/1.6 Georgia,Times,\"Times New Roman\",serif;margin:2rem;max-width:48rem;color:#111;background:#fff} h2{font-size:1.15em;margin:1.2rem 0 .6rem} p{margin:0 0 1rem}</style>\n"
        "</head>\n<body contenteditable=\"true\" spellcheck=\"true\">\n"
        + "\n".join(body)
        + "\n</body>\n</html>\n"
    )


def main():
    ap = argparse.ArgumentParser(description="Extract structured text (paragraphs/headings) from PDF with embedded text.")
    ap.add_argument("--pdf", required=True, help="Input PDF path")
    ap.add_argument("--outdir", default="output_vol2", help="Output directory")
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    all_blocks = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        p_blocks = page_blocks_with_roles(page)
        for b in p_blocks:
            all_blocks.append({
                "page": i + 1,
                "role": b["role"],
                "text": b["text"],
                "wsize": b["wsize"],
                "bbox": b["bbox"],
            })

    # Save JSON
    struct = {"file": pdf_path.name, "blocks": all_blocks}
    (outdir / "structured.json").write_text(json.dumps(struct, ensure_ascii=False, indent=2), encoding="utf-8")
    # Save initial HTML/TXT
    (outdir / "structured.html").write_text(to_html(all_blocks, pdf_path.name), encoding="utf-8")
    (outdir / "structured.txt").write_text("\n\n".join(b["text"] for b in all_blocks), encoding="utf-8")
    print(f"Saved: {outdir / 'structured.json'}")
    print(f"Saved: {outdir / 'structured.html'}")
    print(f"Saved: {outdir / 'structured.txt'}")


if __name__ == "__main__":
    main()


