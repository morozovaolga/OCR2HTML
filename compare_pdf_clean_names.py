import argparse
import re
from pathlib import Path

import fitz  # PyMuPDF


NAME_PATTERN = re.compile(r'\b[А-ЯЁ][а-яё]+\b(?:\s+[А-ЯЁ][а-яё]+){0,2}')


def extract_pdf_names(pdf_path: Path):
    names = []
    doc = fitz.open(pdf_path)
    for page in doc:
        text = page.get_text("text").splitlines()
        for line in text:
            line = line.strip()
            if not line:
                continue
            match = NAME_PATTERN.match(line)
            if match:
                names.append(line)
    return names


def extract_clean_names(clean_text: str):
    candidates = []
    for part in clean_text.splitlines():
        part = part.strip()
        if not part:
            continue
        match = NAME_PATTERN.match(part)
        if match:
            candidates.append(part)
    return candidates


def main():
    ap = argparse.ArgumentParser(description="Compare named phrases in modern clean text and original PDF.")
    ap.add_argument("--pdf", required=True, help="PDF with modern spelling")
    ap.add_argument("--clean", required=True, help="final_clean.txt produced by pipeline")
    ap.add_argument("--out", default="name_diff.txt", help="Output file with differences")
    ap.add_argument("--modern-pdf", action="store_true", help="Only run when PDF already in modern orthography")
    args = ap.parse_args()

    if not args.modern_pdf:
        print("Flag --modern-pdf not provided, skipping comparison.")
        return 0

    pdf_path = Path(args.pdf)
    clean_path = Path(args.clean)
    out_path = Path(args.out)

    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return 1
    if not clean_path.exists():
        print(f"Clean text not found: {clean_path}")
        return 1

    pdf_names = extract_pdf_names(pdf_path)
    clean_names = extract_clean_names(clean_path.read_text(encoding="utf-8", errors="ignore"))

    diffs = []
    for pdf_name, clean_name in zip(pdf_names, clean_names):
        if pdf_name != clean_name:
            diffs.append(f"PDF : {pdf_name}\nCLEAN: {clean_name}\n")

    out_path.write_text("\n".join(diffs), encoding="utf-8")
    print(f"Found {len(diffs)} mismatches, saved to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


