import argparse
import re
from pathlib import Path
from html import escape as hesc


LAT_TO_CYR = {
    "A": "А", "a": "а",
    "B": "В", "E": "Е", "e": "е",
    "K": "К", "k": "к",
    "M": "М",
    "H": "Н",
    "O": "О", "o": "о",
    "P": "Р", "p": "р",
    "C": "С", "c": "с",
    "T": "Т",
    "X": "Х", "x": "х",
    "Y": "У", "y": "у",
}


def replace_odd_symbols(text: str) -> str:
    repl = {
        "■": " ",
        "¬": "",
        "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "—", "―": "—",
        "“": "«", "”": "»", "„": "«", "‟": "»",
    }
    for a, b in repl.items():
        text = text.replace(a, b)
    return text


def convert_mixed_latin_to_cyr(text: str) -> str:
    token_re = re.compile(r"[A-Za-z\u0400-\u04FF]+(?:-[A-Za-z\u0400-\u04FF]+)*")
    def fix(m: re.Match) -> str:
        tok = m.group(0)
        has_cyr = re.search(r"[\u0400-\u04FF]", tok)
        has_lat = re.search(r"[A-Za-z]", tok)
        if not (has_cyr and has_lat):
            return tok
        return "".join(LAT_TO_CYR.get(ch, ch) for ch in tok)
    return token_re.sub(fix, text)


def join_spaced_letters(text: str) -> str:
    # "В ы р е з к а" -> "Вырезка"
    return re.sub(r"(?<!\S)(?:[А-ЯЁа-яё]\s){2,}[А-ЯЁа-яё](?!\S)",
                  lambda m: m.group(0).replace(" ", ""), text)


def fix_intraword_small_gaps(text: str) -> str:
    # Join cases like "обни мают" when parts are mostly short
    def _sub(m: re.Match) -> str:
        seg = m.group(0)
        parts = seg.split()
        short = sum(1 for p in parts if len(p) <= 2)
        if len(parts) >= 2 and (short >= len(parts) - 1) and len("".join(parts)) >= 4:
            return "".join(parts)
        return seg
    return re.sub(r"(?<![\w-])(?:[А-ЯЁа-яё]+(?:\s+[А-ЯЁа-яё]+)+)(?![\w-])", _sub, text)




def fix_common_ocr_errors(text: str) -> str:
    # Fix common OCR errors: "па" -> "на", "то" -> "по" (in context), etc.
    # Be careful: only fix in specific contexts to avoid false positives
    fixes = [
        # "па" -> "на" (before any word starting with lowercase cyrillic)
        # This covers cases like "па дитя", "па столе", "па земле"
        (r"\bпа\s+([а-яё])", r"на \1"),
        # "то" -> "по" (in some contexts like "то дороге", "то стене")
        (r"\bто\s+(дороге|стене|полу|небу|земле|воде|берегу|берегам)\b", r"по \1"),
        # "то" -> "по" in "то мере", "то степени"
        (r"\bто\s+(мере|степени|крайней|меньшей|большей)\b", r"по \1"),
    ]
    for pattern, replacement in fixes:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def cleanup_text(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[\u200B\u200C\u200D\u00AD]", "", t)
    t = replace_odd_symbols(t)
    # Em dash spacing: unify and ensure spaces on both sides
    t = t.replace("–", "—")
    t = re.sub(r"\s*—\s*", " — ", t)
    # Dehyphenate across newlines (already normalized, but keep it safe)
    t = re.sub(r"([\wА-Яа-яЁё])[-\-\–\—]\n(?=[\wА-Яа-яЁё])", r"\1", t)
    # Merge single line breaks inside paragraphs
    t = re.sub(r"(?<!\n)\n(?!\n)", " ", t)
    # Collapse spaces
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = join_spaced_letters(t)
    t = fix_intraword_small_gaps(t)
    t = fix_common_ocr_errors(t)
    t = convert_mixed_latin_to_cyr(t)
    return t.strip()


def to_html(text: str, title: str) -> str:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    body = "\n".join(f"<p>{hesc(p)}</p>" for p in paras)
    return (
        "<!doctype html>\n<html lang=\"ru\">\n<head>\n"
        "<meta charset=\"utf-8\"/>\n"
        f"<title>{hesc(title)}</title>\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/>\n"
        "<style>body{font:18px/1.6 Georgia,Times,\"Times New Roman\",serif;margin:2rem;max-width:48rem;color:#111;background:#fff} p{margin:0 0 1rem}</style>\n"
        "</head>\n<body>\n" + body + "\n</body>\n</html>\n"
    )


def main():
    ap = argparse.ArgumentParser(description="Post-cleanup: join spaced letters, fix intraword gaps, Latin→Cyr mix. Saves TXT/HTML.")
    ap.add_argument("--in", dest="inp", required=True, help="Входной TXT")
    ap.add_argument("--out", dest="out", required=True, help="Выходной TXT")
    ap.add_argument("--html", dest="html", help="Необязательный путь для HTML")
    ap.add_argument("--title", default="После доп. очистки", help="Заголовок HTML")
    args = ap.parse_args()

    src = Path(args.inp)
    dst = Path(args.out)
    text = src.read_text(encoding="utf-8", errors="replace")
    cleaned = cleanup_text(text)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(cleaned, encoding="utf-8")
    if args.html:
        Path(args.html).write_text(to_html(cleaned, args.title), encoding="utf-8")
    print(f"Saved: {dst}" + (f", {args.html}" if args.html else ""))


if __name__ == "__main__":
    main()
