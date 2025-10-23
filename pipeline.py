import argparse
import subprocess
from pathlib import Path


def run(cmd: list[str]):
    print("$", " ".join(cmd))
    subprocess.check_call(cmd)


def main():
    ap = argparse.ArgumentParser(description="PDF (с OCR текстовым слоем) -> структурированный HTML/TXT с корректурой")
    ap.add_argument("--pdf", required=True, help="Входной PDF с текстовым слоем (после OCR)")
    ap.add_argument("--outdir", default="out", help="Папка вывода (по умолчанию: out)")
    ap.add_argument("--title", default="Документ (современная орфография)", help="Заголовок HTML")
    args = ap.parse_args()

    here = Path(__file__).parent
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # 1) Извлечь структуру из PDF
    run(["python", str(here / "extract_structured_text.py"), "--pdf", args.pdf, "--outdir", str(outdir)])

    # 2) Применить oldspelling правила ко всем блокам
    run(["python", str(here / "apply_rules_structured.py"), "--rules", str(here / "oldspelling.py"), "--in", str(outdir / "structured.json"), "--out", str(outdir / "structured_rules.json")])

    # 3) Современная орфография/типографика + слияние абзацев + HTML/TXT/flags
    run(["python", str(here / "modernize_structured.py"), "--in", str(outdir / "structured_rules.json"), "--outdir", str(outdir), "--title", args.title])

    print("\nГотово.")
    print("Откройте:")
    print(" -", outdir / "final.html")
    print(" -", outdir / "final.txt")
    print(" -", outdir / "flags.json")


if __name__ == "__main__":
    main()

