OCR → HTML (paragraph-preserving, with spelling modernization)

This minimal toolchain takes a PDF that already contains an OCR text layer, reconstructs paragraphs/headings based on page layout, applies historical (pre‑reform) Russian spelling rules (oldspelling), then modern Russian spelling/typographic normalization, and exports clean HTML/TXT. Also supports EPUB file generation with automatically created cover based on a template.

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
  - Basic (paragraph preservation + spelling correction):
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "My Document (modern)"
  - With optional steps:
  - Add LanguageTool (cloud) and post-cleanup (optionally followed by Yandex.Speller):
      - python pipeline.py --pdf path/to/file.pdf --outdir out --title "My Document" --lt-cloud --with-yandex --post-clean
  - For PDFs with two columns per page (left column first, then right):
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "My Document" --two-columns
  - With EPUB generation (requires EPUB template and Pillow; `final_clean.txt` must exist):
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "My Document" --lt-cloud --epub-template sample.epub --epub-author "Author Name"
    - (Optional) add `--epub-max-chapter-size KB` to force splitting into sized chapters when there are no clear headings (default 50)

Outputs (in out/)
- structured.json — block structure per page (roles: heading/paragraph)
- structured.html / structured.txt — preview after structuring
- structured_rules.json — result after applying oldspelling rules
- final.html — modern spelling/typography, paragraph‑preserving (main output)
- final.txt — modernized plain text
- flags.json — flagged ambiguous letter changes (for review)
Optional (if enabled):
- final_clean.txt / final_clean.html — after safe LanguageTool (cloud) fixes
- final_better.txt / final_better.html — after post-cleanup (join spaced letters, Latin→Cyrillic)
- final_gigachat.txt / final_gigachat.html — after GigaChat API correction (grammar and OCR errors)
- Book_Title.epub — EPUB file with automatically generated cover (if --epub-template is specified)

How it works
1) extract_structured_text.py — collects text blocks via PyMuPDF and assigns roles.
2) apply_rules_structured.py — loads (pattern, replacement) pairs from oldspelling.py and applies them to all blocks.
3) modernize_structured.py — fixes linebreaks/dashes/ellipsis/spaces, merges paragraph fragments, modernizes letters, writes final HTML/TXT and flags.
4) (optional) lt_cloud.py — applies safe LanguageTool (cloud) spelling fixes.
5) (optional) post_cleanup.py — joins spaced letters, fixes intraword gaps, converts Latin→Cyrillic.
6) (optional) gigachat_check.py — AI-powered grammar and OCR error correction.

How LanguageTool and Yandex.Speller work together:
LanguageTool is a cloud-based grammar and spelling checker. This project uses it only for safe automatic corrections, without changing style or grammar.

What it does:
1. Sends text in chunks (by paragraphs, up to 6000 characters by default, adjustable via `--chunk-size`) to the LanguageTool cloud API
2. Receives a list of found errors and suggested fixes
3. Applies only "safe" fixes:
   - Spelling errors (MORFOLOGIK) — e.g., "машына" → "машина", "карова" → "корова"
   - Whitespace (WHITESPACE, SPACE) — extra or missing spaces
   - Multiple spaces (MULTIPLE_SPACES) — "two   spaces" → "two spaces"
   - Double punctuation (DOUBLE_PUNCTUATION) — "??" → "?"
4. Applies the first suggested fix for each safe match and avoids overlapping corrections
5. Optionally (`--with-yandex`) runs Yandex.Speller after LanguageTool for an extra pass of simple spelling fixes (language override via `--yandex-lang`)

What it does NOT do:
- Does not fix style
- Does not change grammar (only spelling)
- Does not fix complex OCR errors (e.g., "ялучше" → "я лучше")
- Does not work with contextual errors

Result: final_clean.txt and final_clean.html files with applied safe corrections.

Setting up GigaChat API (experimental, may not work):
⚠️ WARNING: Connecting to GigaChat API may require installing NUC (National Certification Center) certificates and additional setup. It is recommended to use Ollama instead of GigaChat.

If you still want to try:
1. Register at https://developers.sber.ru/ and get Client ID and Client Secret
2. Install dependencies (if not already installed):
   pip install python-dotenv
3. Install NUC certificates according to instructions at https://developers.sber.ru/docs/ru/gigachat/api/overview
4. Create a .env file in the project root:
   - Open .env and fill in your values:
     GIGACHAT_CLIENT_ID=your_client_id
     GIGACHAT_CLIENT_SECRET=your_client_secret
     # Or use a ready-made Authorization Key:
     GIGACHAT_AUTH_KEY=your_authorization_key_in_base64
   
   Alternative: set environment variables in the system:
   - Windows PowerShell:
     $env:GIGACHAT_CLIENT_ID="your_client_id"
     $env:GIGACHAT_CLIENT_SECRET="your_client_secret"
   - Linux/macOS:
     export GIGACHAT_CLIENT_ID="your_client_id"
     export GIGACHAT_CLIENT_SECRET="your_client_secret"

EPUB Generation (--epub-template):
The program can automatically create EPUB files based on an EPUB template and processed text.

Requirements:
1. EPUB template file (e.g., sample.epub) in project root or specify path
2. Pillow installed: pip install Pillow

What it does:
1. Uses the best available text source (priority: final_gigachat.html > final_better.html > final_clean.txt > final_clean.html > final.txt > structured_rules.json > structured.json)
2. When reading `.txt` (e.g., `final_clean.txt`), paragraphs that start with `Часть`, `Глава`, `Раздел`, `Книга` (with a number), `***`, or a Roman numeral are treated as headings so the text can still be split into chapters even without markup
3. Splits text into sections — by headings when present, otherwise by size (controlled by `--max-chapter-size`, defaults to ~50 KB) — so no paragraph disappears and you don’t end up with a single enormous file
4. Automatically generates cover with title and author (random gradient from 3 harmonious colors)
5. Updates title page and table of contents
6. Creates EPUB file in out/ folder (skipped if `final_clean.txt` is missing)
7. `generate_epub.py` can read plain `.txt` files (e.g., `final_clean.txt` from LanguageTool), so EPUB always uses the latest corrected text

Example usage:
```bash
# Full processing with EPUB generation
python pipeline.py --pdf book.pdf --outdir out --title "Book Title" --two-columns --no-oldspelling --lt-cloud --epub-template sample.epub --epub-author "Author Name"

# Or separately (if you already have processed HTML)
python generate_epub.py --template sample.epub --in out/final_better.html --out out/book.epub --title "Book Title" --author "Author Name"
```

Optional name-validation step (PDF must already be in modern spelling):
```bash
python compare_pdf_clean_names.py --pdf book.pdf --clean out/final_clean.txt --modern-pdf --out out/name_diff.txt
```
The script lists mismatches between title-like phrases extracted from the PDF and the cleaned text to highlight typos before EPUB finalization.

Natasha (NER) for richer entity comparison:
```bash
python natasha_entity_check.py --pdf sn.pdf --clean out/final_clean.txt --out out/sn_natasha.txt --types PER,LOC,ORG
```
This utility extracts named entities (persons, locations, organizations) with Natasha and compares their normalized forms between the PDF and `final_clean.txt`, reporting only entities that appear in one source but not the other. Use `--types PER,LOC` to include or exclude classes.

Natasha-based harmonization:
```bash
python natasha_sync.py --pdf sn.pdf --clean out/final_clean.txt --report out/sn_natasha_sync.txt --types PER,LOC,ORG
```
It rewrites `final_clean.txt`, replacing the entity strings that survived the modernization step with the forms from the PDF, so the EPUB can reuse the verified names and geographies.

Run both steps inside `pipeline.py` with:
```bash
python pipeline.py ... --natasha-check --natasha-sync --natasha-out out/sn_natasha.txt --natasha-sync-report out/sn_natasha_sync.txt
```
The flags `--natasha-types`, `--natasha-check`, and `--natasha-sync` sequentially run the Natasha comparison and harmonization before EPUB generation.

Context check:
```bash
python context_checker.py --in out/final_clean.txt --out out/context_warnings.txt --pronouns он,она,оно,они
```
This script uses `pymorphy2` to look for pronoun + following-word pairs where the second word is not parsed as a verb or infinitive and reports the surrounding sentence. You can override the pronoun set via `--context-pronouns`.

Enable the context step inside `pipeline.py`:
```bash
python pipeline.py ... --context-check --context-out out/context_warnings.txt --natasha-check --natasha-sync
```
`--context-check` runs `context_checker.py` immediately after LanguageTool so the EPUB is built from text that passed the pronoun+verb sanity check.

`pyspellchecker` can be added as another lightweight pass to catch rare typos that LanguageTool misses.

Features:
- Automatic cover generation with gradient from 3 harmonious colors
- Sections numbered starting from 1 (Section0001.xhtml, Section0002.xhtml, etc.)
- Updated title page (Titul.xhtml) with new title and author
- Updated table of contents (toc.ncx) with new sections
- Supports both HTML (final_*.html) and JSON (structured*.json) as source

Repository layout
- pipeline.py                 — orchestrator
- extract_structured_text.py  — structure extraction
- apply_rules_structured.py   — oldspelling rules application
- modernize_structured.py     — modernization and final rendering
- lt_cloud.py                  — LanguageTool (cloud) safe fixes
- post_cleanup.py             — post-cleanup: join spaced letters, fix gaps, Latin→Cyrillic
- gigachat_check.py           — GigaChat API integration (experimental)
- generate_epub.py            — EPUB generation from HTML/JSON with automatic cover
- natasha_entity_check.py      — optional named-entity comparison (PER/LOC/ORG) between PDF and final_clean.txt via Natasha
- natasha_sync.py              — harmonize `final_clean.txt` with PDF entity forms via Natasha
- context_checker.py           — context-sensitive pronoun+verb check
- oldspelling.py              — pre‑reform spelling rules (regex map)
- requirements.txt            — dependencies (PyMuPDF, python-dotenv, Pillow)

Publish to GitHub (example)
- cd ocr2html
- git init -b main
- git add .
- git commit -m "Initial OCR→HTML toolchain"
- git remote add origin https://github.com/<your-user>/<your-repo>.git
- git push -u origin main

