import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]):
    print("$", " ".join(cmd))
    subprocess.check_call(cmd)


def main():
    ap = argparse.ArgumentParser(
        description="PDF (with OCR text layer) -> structured HTML/TXT with paragraph preservation and spelling modernization"
    )
    ap.add_argument("--pdf", required=True, help="Input PDF with OCR text layer")
    ap.add_argument("--outdir", default="out", help="Output directory (default: out)")
    ap.add_argument("--title", default="Document (modern Russian)", help="HTML title")
    ap.add_argument("--no-oldspelling", action="store_true", help="Skip applying rules from oldspelling.py")
    ap.add_argument("--lt-cloud", action="store_true", help="Run LanguageTool (cloud) safe fixes after modernization")
    ap.add_argument("--with-yandex", action="store_true", help="After LanguageTool, pass text through Yandex.Speller as an extra layer")
    ap.add_argument("--yandex-lang", default="ru", help="Language code for Yandex.Speller (default: ru)")
    ap.add_argument("--chunk-size", type=int, default=6000, help="Maximum characters per LanguageTool/Yandex request (default: 6000)")
    ap.add_argument("--post-clean", action="store_true", help="Run post-cleanup: join spaced letters, fix intraword gaps, Latin→Cyrillic")
    ap.add_argument("--gigachat", action="store_true", help="Run GigaChat API grammar and OCR error correction (requires GIGACHAT_CLIENT_ID and GIGACHAT_CLIENT_SECRET env vars)")
    ap.add_argument("--two-columns", action="store_true", help="Process pages with two columns: left column first, then right column")
    ap.add_argument("--epub-template", nargs='?', const="sample.epub", help="Path to EPUB template file (default: sample.epub in project root). If provided, generates EPUB from the best available HTML/JSON")
    ap.add_argument("--epub-author", default="", help="Author name for EPUB cover generation")
    ap.add_argument("--epub-max-chapter-size", type=int, default=50, help="Maximum chapter size in KB for EPUB sections (default: 50)")
    ap.add_argument(
        "--cover-colors",
        default="",
        help="Пять HEX-цветов (полоска, верхний блок, заголовок, градиент начало, градиент конец)",
    )
    ap.add_argument(
        "--cover-colors",
        default="",
        help="Пять HEX-цветов (stripe, top block, title, art-gradient start, art-gradient end)",
    )
    ap.add_argument("--natasha-types", default="PER,LOC", help="Entity types for Natasha checks (PER, LOC, ORG)")
    ap.add_argument("--natasha-check", action="store_true", help="Compare named entities between PDF and final_clean.txt using Natasha")
    ap.add_argument("--natasha-out", default="natasha_diff.txt", help="Output file for Natasha entity comparison")
    ap.add_argument("--natasha-sync", action="store_true", help="Harmonize final_clean.txt with PDF entity forms via Natasha")
    ap.add_argument("--natasha-sync-report", default="natasha_sync.txt", help="Report written by Natasha harmonization")
    ap.add_argument("--context-check", action="store_true", help="Run context_checker on final_clean.txt after LanguageTool")
    ap.add_argument("--context-out", default="context_warnings.txt", help="Output file for context check warnings")
    ap.add_argument("--context-pronouns", default="он,она,оно,они,мы,вы,ты", help="Comma-separated pronouns to look for in context check")
    args = ap.parse_args()

    here = Path(__file__).parent
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # 1) Extract structure from PDF
    extract_cmd = [sys.executable, str(here / "extract_structured_text.py"), "--pdf", args.pdf, "--outdir", str(outdir)]
    if args.two_columns:
        extract_cmd.append("--two-columns")
    run(extract_cmd)

    # 2) (optional) Apply oldspelling rules to blocks
    structured_in = outdir / "structured.json"
    if not args.no_oldspelling:
        run([sys.executable, str(here / "apply_rules_structured.py"), "--rules", str(here / "oldspelling.py"), "--in", str(outdir / "structured.json"), "--out", str(outdir / "structured_rules.json")])
        structured_in = outdir / "structured_rules.json"

    # 3) Modernize spelling/typography + merge paragraphs + HTML/TXT/flags
    run([sys.executable, str(here / "modernize_structured.py"), "--in", str(structured_in), "--outdir", str(outdir), "--title", args.title])

    # 4) (optional) LanguageTool cloud: write final_clean.*
    if args.lt_cloud:
        lt_cmd = [
            sys.executable, str(here / "lt_cloud.py"),
            "--in", str(outdir / "final.txt"),
            "--outdir", str(outdir),
            "--title", args.title + " (LT)",
            "--chunk-size", str(args.chunk_size),
        ]
        if args.with_yandex:
            lt_cmd.append("--with-yandex")
            lt_cmd.extend(["--yandex-lang", args.yandex_lang])
        run(lt_cmd)

    if args.context_check:
        final_clean_txt = outdir / "final_clean.txt"
        if not final_clean_txt.exists():
            print(f"Warning: {final_clean_txt.name} не найден — контекстная проверка пропущена.")
        else:
            run([
                sys.executable,
                str(here / "context_checker.py"),
                "--in", str(final_clean_txt),
                "--out", str(outdir / args.context_out),
                "--pronouns", args.context_pronouns,
            ])

    # 5) (optional) Post-cleanup: write final_better.* from final_clean.txt if present, else final.txt
    if args.post_clean:
        source_txt = outdir / ("final_clean.txt" if (outdir / "final_clean.txt").exists() else "final.txt")
        run([sys.executable, str(here / "post_cleanup.py"), "--in", str(source_txt), "--out", str(outdir / "final_better.txt"), "--html", str(outdir / "final_better.html"), "--title", args.title + " (post-clean)"])

    # 6) (optional) GigaChat API: write final_gigachat.* from best available source
    if args.gigachat:
        source_txt = outdir / ("final_better.txt" if (outdir / "final_better.txt").exists() else 
                              "final_clean.txt" if (outdir / "final_clean.txt").exists() else 
                              "final.txt")
        run([sys.executable, str(here / "gigachat_check.py"), "--in", str(source_txt), "--outdir", str(outdir), "--title", args.title + " (GigaChat)"])

    # 8) (optional) Generate EPUB from template
    if args.epub_template:
        final_clean_txt = outdir / "final_clean.txt"
        if not final_clean_txt.exists():
            print(f"Warning: {final_clean_txt.name} не найден — EPUB пропущен.")
        else:
            template_epub = Path(args.epub_template)
        # Если путь относительный, пробуем найти в корне проекта
        if not template_epub.is_absolute():
            if (here / template_epub).exists():
                template_epub = here / template_epub
            elif (here / "sample.epub").exists():
                template_epub = here / "sample.epub"
        if not template_epub.exists():
            print(f"Warning: EPUB template not found: {template_epub}")
        else:
            # Определяем лучший источник: HTML или JSON
            # Приоритет: final_gigachat.html > final_better.html > final_clean.html > final.html
            # Или structured_rules.json > structured.json
            candidates = [
                outdir / "final_gigachat.html",
                outdir / "final_better.html",
                outdir / "final_clean.txt",
                outdir / "final_clean.html",
                outdir / "final.txt",
                outdir / "structured_rules.json",
                outdir / "structured.json",
            ]
            source_file = None
            for candidate in candidates:
                if candidate.exists():
                    source_file = candidate
                    break
            
            if source_file and source_file.exists():
                output_epub = outdir / f"{args.title.replace(' ', '_')}.epub"
                epub_cmd = [
                    sys.executable,
                    str(here / "generate_epub.py"),
                    "--template", str(template_epub),
                    "--in", str(source_file),
                    "--out", str(output_epub),
                    "--title", args.title,
                ]
                if args.epub_author:
                epub_cmd.extend(["--author", args.epub_author])
                if args.cover_colors:
                    epub_cmd.extend(["--cover-colors", args.cover_colors])
                epub_cmd.extend(["--max-chapter-size", str(args.epub_max_chapter_size)])
                run(epub_cmd)
            else:
                print("Warning: No suitable source file found for EPUB generation")

    if args.natasha_check:
        final_clean_txt = outdir / "final_clean.txt"
        if not final_clean_txt.exists():
            print(f"Warning: {final_clean_txt.name} не найден — Natasha-сравнение пропущено.")
        else:
            run([
                sys.executable,
                str(here / "natasha_entity_check.py"),
                "--pdf", args.pdf,
                "--clean", str(final_clean_txt),
                "--out", str(outdir / args.natasha_out),
                "--types", args.natasha_types,
            ])

    if args.natasha_sync:
        final_clean_txt = outdir / "final_clean.txt"
        if not final_clean_txt.exists():
            print(f"Warning: {final_clean_txt.name} не найден — Natasha-грамминг пропущен.")
        else:
            run([
                sys.executable,
                str(here / "natasha_sync.py"),
                "--pdf", args.pdf,
                "--clean", str(final_clean_txt),
                "--types", args.natasha_types,
                "--report", str(outdir / args.natasha_sync_report),
            ])

    print("\nDone.")
    print("Open:")
    print(" -", outdir / "final.html")
    print(" -", outdir / ("final_clean.html" if (outdir / "final_clean.html").exists() else "final.html"))
    print(" -", outdir / ("final_better.html" if (outdir / "final_better.html").exists() else "final.html"))
    print(" -", outdir / ("final_gigachat.html" if (outdir / "final_gigachat.html").exists() else "final.html"))


if __name__ == "__main__":
    main()

