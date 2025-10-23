import argparse
import json
import time
from html import escape as hesc
from pathlib import Path
from typing import List
from urllib import request, parse


SAFE_RULE_SUBSTR = (
    'MORFOLOGIK',   # spelling
    'WHITESPACE',   # generic whitespace
    'SPACE',        # any *_SPACE*
    'MULTIPLE_SPACES',
    'DOUBLE_PUNCTUATION',
)


def is_safe(rule_id: str) -> bool:
    rid = (rule_id or '').upper()
    return any(s in rid for s in SAFE_RULE_SUBSTR)


def chunks_by_paragraphs(text: str, max_len: int = 6000) -> List[str]:
    paras = text.split("\n\n")
    out, buf = [], []
    cur = 0
    for p in paras:
        piece = p + "\n\n"
        if cur + len(piece) > max_len and buf:
            out.append("".join(buf))
            buf, cur = [], 0
        buf.append(piece)
        cur += len(piece)
    if buf:
        out.append("".join(buf))
    return out


def cloud_check(text: str, lang: str = 'ru-RU', timeout: int = 60):
    url = 'https://api.languagetool.org/v2/check'
    data = parse.urlencode({'text': text, 'language': lang}).encode('utf-8')
    req = request.Request(url, data=data, headers={
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    })
    with request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read().decode('utf-8', errors='replace')
    try:
        return json.loads(payload).get('matches', [])
    except Exception:
        return []


def apply_matches(text: str, matches) -> str:
    # Apply first replacement for each safe, non-overlapping match
    matches = [m for m in matches if is_safe((m.get('rule') or {}).get('id'))]
    matches.sort(key=lambda m: m.get('offset', 0))
    res, i, last_end = [], 0, 0
    for m in matches:
        start = m.get('offset', 0)
        length = m.get('length', 0)
        end = start + length
        if start < last_end:
            continue
        reps = m.get('replacements') or []
        rep = reps[0].get('value') if reps else None
        if rep is None:
            continue
        res.append(text[i:start])
        res.append(rep)
        i = end
        last_end = end
    res.append(text[i:])
    return "".join(res)


def to_html(text: str, title: str) -> str:
    return (
        "<!doctype html>\n<html lang=\"ru\">\n<head>\n"
        "<meta charset=\"utf-8\"/>\n"
        f"<title>{hesc(title)}</title>\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/>\n"
        "<style>body{font:18px/1.6 Georgia,Times,\"Times New Roman\",serif;margin:2rem;max-width:48rem;color:#111;background:#fff} pre{white-space:pre-wrap}</style>\n"
        "</head>\n<body>\n<pre contenteditable=\"true\" spellcheck=\"true\">" + hesc(text) + "</pre>\n</body>\n</html>\n"
    )


def main():
    ap = argparse.ArgumentParser(description='Apply safe LanguageTool (cloud) fixes without extra deps.')
    ap.add_argument('--in', dest='inp', required=True, help='Входной TXT')
    ap.add_argument('--outdir', default='out', help='Папка вывода')
    ap.add_argument('--title', default='Документ (LT)', help='Заголовок HTML')
    ap.add_argument('--sleep', type=float, default=0.5, help='Пауза между запросами (сек)')
    ap.add_argument('--timeout', type=int, default=60, help='Таймаут HTTP (сек)')
    args = ap.parse_args()

    inp = Path(args.inp)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    text = inp.read_text(encoding='utf-8', errors='replace')
    parts = chunks_by_paragraphs(text)
    fixed_parts = []
    total_safe = 0
    for part in parts:
        try:
            matches = cloud_check(part, 'ru-RU', timeout=args.timeout)
        except Exception:
            matches = []
        total_safe += sum(1 for m in matches if is_safe((m.get('rule') or {}).get('id')))
        fixed_parts.append(apply_matches(part, matches))
        time.sleep(args.sleep)
    fixed_text = "".join(fixed_parts)
    (outdir / 'final_clean.txt').write_text(fixed_text, encoding='utf-8')
    (outdir / 'final_clean.html').write_text(to_html(fixed_text, args.title), encoding='utf-8')
    print(f'Applied safe fixes: {total_safe}. Saved final_clean.txt/html in {outdir}')


if __name__ == '__main__':
    main()

