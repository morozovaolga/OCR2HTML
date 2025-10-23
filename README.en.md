OCR → HTML (paragraph-preserving, with spelling modernization)

This minimal toolchain takes a PDF that already contains an OCR text layer, reconstructs paragraphs/headings based on page layout, applies historical (pre‑reform) Russian spelling rules (oldspelling), then modern Russian spelling/typographic normalization, and exports clean HTML/TXT.

No frontend or extra files — just the scripts you need.

Requirements
- Python 3.10+
- pip

Install (virtualenv recommended)
- python -m venv .venv
- .venv\Scripts\Activate (Windows) or source .venv/bin/activate (macOS/Linux)
- python -m pip install --upgrade pip
- pip install -r requirements.txt

Quick Start
- Ensure your PDF already has an OCR text layer (this project does not run OCR).
- Run the pipeline:
  - python pipeline.py --pdf path/to/file.pdf --outdir out --title "My Document (modern)"

Outputs (in out/)
- structured.json — block structure per page (roles: heading/paragraph)
- structured.html / structured.txt — preview after structuring
- structured_rules.json — result after applying oldspelling rules
- final.html — modern spelling/typography, paragraph‑preserving (main output)
- final.txt — modernized plain text
- flags.json — flagged ambiguous letter changes (for review)

How it works
1) extract_structured_text.py — collects text blocks via PyMuPDF and assigns roles.
2) apply_rules_structured.py — loads (pattern, replacement) pairs from oldspelling.py and applies them to all blocks.
3) modernize_structured.py — fixes linebreaks/dashes/ellipsis/spaces, merges paragraph fragments, modernizes letters, writes final HTML/TXT and flags.

CLI
- python pipeline.py --pdf t1.pdf --outdir output_vol2 --title "t1.pdf (modern, structured)"
  - --pdf    input PDF (with text layer)
  - --outdir output directory
  - --title  HTML title

Repository layout
- pipeline.py                 — orchestrator
- extract_structured_text.py  — structure extraction
- apply_rules_structured.py   — oldspelling rules application
- modernize_structured.py     — modernization and final rendering
- oldspelling.py              — pre‑reform spelling rules (regex map)
- requirements.txt            — dependencies (PyMuPDF)

Publish to GitHub (example)
- cd ocr2html
- git init -b main
- git add .
- git commit -m "Initial OCR→HTML toolchain"
- git remote add origin https://github.com/<your-user>/<your-repo>.git
- git push -u origin main

