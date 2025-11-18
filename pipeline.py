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
    ap.add_argument("--post-clean", action="store_true", help="Run post-cleanup: join spaced letters, fix intraword gaps, Latin→Cyrillic")
    ap.add_argument("--gigachat", action="store_true", help="Run GigaChat API grammar and OCR error correction (requires GIGACHAT_CLIENT_ID and GIGACHAT_CLIENT_SECRET env vars)")
    ap.add_argument("--ollama", action="store_true", help="Run Ollama (local) grammar and OCR error correction (requires Ollama to be running)")
    ap.add_argument("--ollama-model", default="mistral:latest", help="Ollama model to use (default: mistral:latest)")
    ap.add_argument("--two-columns", action="store_true", help="Process pages with two columns: left column first, then right column")
    ap.add_argument("--epub-template", nargs='?', const="sample.epub", help="Path to EPUB template file (default: sample.epub in project root). If provided, generates EPUB from the best available HTML/JSON")
    ap.add_argument("--epub-author", default="", help="Author name for EPUB cover generation")
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
        run([sys.executable, str(here / "lt_cloud.py"), "--in", str(outdir / "final.txt"), "--outdir", str(outdir), "--title", args.title + " (LT)"])

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

    # 7) (optional) Ollama (local): write final_ollama.* from best available source
    if args.ollama:
        source_txt = outdir / ("final_better.txt" if (outdir / "final_better.txt").exists() else 
                              "final_clean.txt" if (outdir / "final_clean.txt").exists() else 
                              "final.txt")
        ollama_cmd = [sys.executable, str(here / "ollama_check.py"), "--in", str(source_txt), "--outdir", str(outdir), "--title", args.title + " (Ollama)", "--model", args.ollama_model]
        run(ollama_cmd)

    # 8) (optional) Generate EPUB from template
    if args.epub_template:
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
            # Приоритет: final_ollama.html > final_gigachat.html > final_better.html > final_clean.html > final.html
            # Или structured_rules.json > structured.json
            source_file = None
            source_type = None
            
            # Пробуем HTML файлы
            for html_file in [outdir / "final_ollama.html", outdir / "final_gigachat.html", 
                             outdir / "final_better.html", outdir / "final_clean.html", outdir / "final.html"]:
                if html_file.exists():
                    source_file = html_file
                    source_type = "html"
                    break
            
            # Если HTML не найден, пробуем JSON
            if source_file is None:
                for json_file in [outdir / "structured_rules.json", outdir / "structured.json"]:
                    if json_file.exists():
                        source_file = json_file
                        source_type = "json"
                        break
            
            if source_file and source_file.exists():
                output_epub = outdir / f"{args.title.replace(' ', '_')}.epub"
                epub_cmd = [sys.executable, str(here / "generate_epub.py"), 
                           "--template", str(template_epub),
                           "--in", str(source_file),
                           "--out", str(output_epub),
                           "--title", args.title]
                if args.epub_author:
                    epub_cmd.extend(["--author", args.epub_author])
                run(epub_cmd)
            else:
                print("Warning: No suitable source file found for EPUB generation")

    print("\nDone.")
    print("Open:")
    print(" -", outdir / "final.html")
    print(" -", outdir / ("final_clean.html" if (outdir / "final_clean.html").exists() else "final.html"))
    print(" -", outdir / ("final_better.html" if (outdir / "final_better.html").exists() else "final.html"))
    print(" -", outdir / ("final_gigachat.html" if (outdir / "final_gigachat.html").exists() else "final.html"))
    print(" -", outdir / ("final_ollama.html" if (outdir / "final_ollama.html").exists() else "final.html"))


if __name__ == "__main__":
    main()

