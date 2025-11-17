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
    ap.add_argument("--two-columns", action="store_true", help="Process pages with two columns: left column first, then right column")
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

    print("\nDone.")
    print("Open:")
    print(" -", outdir / "final.html")
    print(" -", outdir / ("final_clean.html" if (outdir / "final_clean.html").exists() else "final.html"))
    print(" -", outdir / ("final_better.html" if (outdir / "final_better.html").exists() else "final.html"))


if __name__ == "__main__":
    main()

