import argparse
from pathlib import Path

from natasha_entity_check import (
    Mention,
    collect_mentions,
    load_pdf_text,
    parse_types,
)


def build_replacements(
    pdf_mentions: list[Mention],
    clean_mentions: list[Mention],
) -> list[tuple[Mention, Mention]]:
    pdf_map = {(m.normal, m.type): m for m in pdf_mentions}
    clean_map = {(m.normal, m.type): m for m in clean_mentions}
    replacements = []
    for key, clean_mention in clean_map.items():
        pdf_mention = pdf_map.get(key)
        if not pdf_mention:
            continue
        if clean_mention.text == pdf_mention.text:
            continue
        replacements.append((clean_mention, pdf_mention))
    return replacements


def apply_replacements(text: str, replacements: list[tuple[Mention, Mention]]) -> tuple[str, list[tuple[Mention, Mention, int]]]:
    applied = []
    for clean_mention, pdf_mention in replacements:
        old = clean_mention.text
        new = pdf_mention.text
        if not old or old == new:
            continue
        count = text.count(old)
        if not count:
            continue
        text = text.replace(old, new)
        applied.append((clean_mention, pdf_mention, count))
    return text, applied


def format_sync_report(
    applied: list[tuple[Mention, Mention, int]],
) -> str:
    if not applied:
        return "Замены не применялись: текст уже совпадает с PDF."
    lines = ["Применённые замены (читальный текст → PDF):"]
    for clean_mention, pdf_mention, count in applied:
        lines.append(
            f"- {clean_mention.type}: {clean_mention.text} → {pdf_mention.text} (заменено {count} раз)"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Гармонизирует final_clean.txt с упоминаниями из PDF.")
    parser.add_argument("--pdf", required=True, help="PDF с эталонными сущностями")
    parser.add_argument("--clean", required=True, help="final_clean.txt для правки")
    parser.add_argument("--out", help="Если указан, сохраняет результат в отдельный файл; иначе перезаписывает `clean`")
    parser.add_argument("--report", help="Файл для отчёта по заменам")
    parser.add_argument("--types", default="PER,LOC", help="Типы сущностей (PER, LOC, ORG)")
    parser.add_argument("--keep-order", action="store_true", help="Не удалять дубликаты сущностей")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    clean_path = Path(args.clean)

    for path in (pdf_path, clean_path):
        if not path.exists():
            parser.error(f"Файл не найден: {path}")

    allowed = parse_types(args.types)

    pdf_text = load_pdf_text(pdf_path)
    clean_text = clean_path.read_text(encoding="utf-8", errors="ignore")

    pdf_mentions = collect_mentions(pdf_text, allowed, deduplicate=not args.keep_order)
    clean_mentions = collect_mentions(clean_text, allowed, deduplicate=not args.keep_order)

    replacements = build_replacements(pdf_mentions, clean_mentions)
    new_text, applied = apply_replacements(clean_text, replacements)

    target_path = Path(args.out) if args.out else clean_path
    target_path.write_text(new_text, encoding="utf-8")

    report = format_sync_report(applied)
    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
    else:
        print(report)

    print(f"Гармонизация выполнена, сохранил: {target_path}")


if __name__ == "__main__":
    main()

