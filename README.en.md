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
  - Basic (paragraph preservation + spelling correction):
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "My Document (modern)"
  - With optional steps:
    - Add LanguageTool (cloud) and post-cleanup:
      - python pipeline.py --pdf path/to/file.pdf --outdir out --title "My Document" --lt-cloud --post-clean
  - For PDFs with two columns per page (left column first, then right):
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "My Document" --two-columns
  - With Ollama grammar correction (recommended, local):
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "My Document" --ollama
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "My Document" --ollama --ollama-model llama3.1:8b
  - With EPUB generation (requires EPUB template and Pillow):
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "My Document" --epub-template sample.epub --epub-author "Author Name"

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
- final_ollama.txt / final_ollama.html — after Ollama correction (local, grammar and OCR errors)
- Book_Title.epub — EPUB file with automatically generated cover (if --epub-template is specified)

How it works
1) extract_structured_text.py — collects text blocks via PyMuPDF and assigns roles.
2) apply_rules_structured.py — loads (pattern, replacement) pairs from oldspelling.py and applies them to all blocks.
3) modernize_structured.py — fixes linebreaks/dashes/ellipsis/spaces, merges paragraph fragments, modernizes letters, writes final HTML/TXT and flags.
4) (optional) lt_cloud.py — applies safe LanguageTool (cloud) spelling fixes.
5) (optional) post_cleanup.py — joins spaced letters, fixes intraword gaps, converts Latin→Cyrillic.
6) (optional) gigachat_check.py or ollama_check.py — AI-powered grammar and OCR error correction.

How LanguageTool (--lt-cloud) works:
LanguageTool is a cloud-based grammar and spelling checker. This project uses it only for safe automatic corrections.

What it does:
1. Sends text in chunks (by paragraphs, up to 6000 characters) to LanguageTool cloud API
2. Receives a list of found errors and suggested fixes
3. Applies only "safe" fixes:
   - Spelling errors (MORFOLOGIK) — e.g., "машына" → "машина", "карова" → "корова"
   - Whitespace (WHITESPACE, SPACE) — extra or missing spaces
   - Multiple spaces (MULTIPLE_SPACES) — "two   spaces" → "two spaces"
   - Double punctuation (DOUBLE_PUNCTUATION) — "??" → "?"
4. Ignores stylistic and grammar rules — only safe spelling corrections
5. Applies the first suggested fix for each safe match
6. Avoids overlapping corrections

What it does NOT do:
- Does not fix style
- Does not change grammar (only spelling)
- Does not fix complex OCR errors (e.g., "ялучше" → "я лучше")
- Does not work with contextual errors

Result: final_clean.txt and final_clean.html files with applied safe corrections.

Setting up Ollama (recommended, easiest):
1. Install Ollama from https://ollama.com/
2. Pull a model (e.g., mistral:latest):
   ollama pull mistral:latest
3. Ensure Ollama is running (usually starts automatically)
4. Use --ollama flag in pipeline.py

Processing large files with Ollama (background mode):
Processing large files can take a long time (hours). You can run the process in the background with logging.

Option 1: Use ready-made scripts (recommended)
- PowerShell: .\run_ollama_background.ps1
- BAT file: run_ollama_background.bat

These scripts run the process in a separate window with automatic logging to out/ollama_log.txt

Option 2: Manual run with logging
```bash
python ollama_check.py --in out/final_better.txt --outdir out --title "Document" --model mistral:latest --log-file out/ollama_log.txt
```

Option 3: Test mode (process only first chunk)
```bash
python ollama_check.py --in out/final_better.txt --outdir out --title "Document" --model mistral:latest --test-first
```
After processing the first chunk, the script will ask whether to continue processing the remaining parts.

Checking progress:
- Open log file: notepad out/ollama_log.txt
- Or watch in real time (PowerShell):
  Get-Content out/ollama_log.txt -Wait -Tail 20

⚠️ IMPORTANT: The computer should NOT go to sleep mode!
If the computer goes to sleep, the process will stop.

To prevent sleep mode (requires administrator rights):
```powershell
# Disable sleep mode
powercfg /change standby-timeout-ac 0
powercfg /change standby-timeout-dc 0

# Restore (when processing is complete)
powercfg /change standby-timeout-ac 30
powercfg /change standby-timeout-dc 15
```

Or configure in Windows: Control Panel → Power Options → Change plan settings → Turn off display: Never, Put computer to sleep: Never

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
1. Uses the best available text source (priority: final_ollama.html > final_gigachat.html > final_better.html > final_clean.html > final.html)
2. Splits text into sections (by headings or size, up to 50 KB per section)
3. Automatically generates cover with title and author (random gradient from 3 harmonious colors)
4. Updates title page and table of contents
5. Creates EPUB file in out/ folder

Example usage:
```bash
# Full processing with EPUB generation
python pipeline.py --pdf book.pdf --outdir out --title "Book Title" --two-columns --no-oldspelling --lt-cloud --epub-template sample.epub --epub-author "Author Name"

# Or separately (if you already have processed HTML)
python generate_epub.py --template sample.epub --in out/final_ollama.html --out out/book.epub --title "Book Title" --author "Author Name"
```

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
- ollama_check.py             — Ollama integration (local AI)
- generate_epub.py            — EPUB generation from HTML/JSON with automatic cover
- run_ollama_background.ps1    — PowerShell script for background Ollama processing
- run_ollama_background.bat    — BAT script for background Ollama processing
- oldspelling.py              — pre‑reform spelling rules (regex map)
- requirements.txt            — dependencies (PyMuPDF, python-dotenv, Pillow)

Publish to GitHub (example)
- cd ocr2html
- git init -b main
- git add .
- git commit -m "Initial OCR→HTML toolchain"
- git remote add origin https://github.com/<your-user>/<your-repo>.git
- git push -u origin main

