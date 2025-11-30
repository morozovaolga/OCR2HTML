OCR → EPUB (paragraph-preserving, with spelling modernization)

This minimal toolchain takes a PDF that already contains an OCR text layer, reconstructs paragraphs/headings based on page layout, applies historical (pre‑reform) Russian spelling rules (oldspelling), then modern Russian spelling/typographic normalization, and exports clean HTML/TXT/EPUB. Main goal is EPUB file generation with automatically created cover based on a template.

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
  - python pdf_to_epub.py --pdf path/to/file.pdf --outdir out --title "My Document (modern)" --epub-template sample.epub
  - With optional steps:
  - Add LanguageTool (cloud) and post-cleanup:
      - python pdf_to_epub.py --pdf path/to/file.pdf --outdir out --title "My Document" --lt-cloud --post-clean --epub-template sample.epub
  - **Recommended:** `--lt-cloud --natasha-sync` for best quality (79.61% accuracy) — see [interactive dashboard with test results](https://morozovaolga.github.io/ocr2epub/)
  - For PDFs with two columns per page (left column first, then right):
    - python pdf_to_epub.py --pdf path/to/file.pdf --outdir out --title "My Document" --two-columns --epub-template sample.epub
  - With EPUB generation (requires EPUB template and Pillow):
    - python pdf_to_epub.py --pdf path/to/file.pdf --outdir out --title "My Document" --author "Author Name" --lt-cloud --epub-template sample.epub
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
- Book_Title.epub — EPUB file with automatically generated cover (if --epub-template is specified)

How it works
1) extract_structured_text.py — collects text blocks via PyMuPDF and assigns roles.
2) apply_rules_structured.py — loads (pattern, replacement) pairs from oldspelling.py and applies them to all blocks.
3) modernize_structured.py — fixes linebreaks/dashes/ellipsis/spaces, merges paragraph fragments, modernizes letters, writes final HTML/TXT and flags.
4) (optional) lt_cloud.py — applies safe LanguageTool (cloud) spelling fixes.
5) (optional) post_cleanup.py — joins spaced letters, fixes intraword gaps, converts Latin→Cyrillic.
How LanguageTool works:
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

What it does NOT do:
- Does not fix style
- Does not change grammar (only spelling)
- Does not fix complex OCR errors (e.g., "ялучше" → "я лучше")
- Does not work with contextual errors

Result: final_clean.txt and final_clean.html files with applied safe corrections.

📊 **[Interactive dashboard](https://morozovaolga.github.io/ocr2epub/)** — visualize test results for all tool combinations. Experiment with different combinations and see their impact on quality metrics in real time.

EPUB Generation (--epub-template):
The program can automatically create EPUB files based on an EPUB template and processed text.

Requirements:
1. EPUB template file (e.g., sample.epub) in project root or specify path
2. Pillow installed: pip install Pillow

What it does:
1. Uses the best available text source (priority: final_better.html > final_clean.txt > final_clean.html > final.txt > structured_rules.json > structured.json)
2. When reading `.txt` (e.g., `final_clean.txt`), paragraphs that start with `Часть`, `Глава`, `Раздел`, `Книга` (with a number), `***`, or a Roman numeral are treated as headings so the text can still be split into chapters even without markup
3. Splits text into sections — by headings when present, otherwise by size (controlled by `--max-chapter-size`, defaults to ~50 KB) — so no paragraph disappears and you don’t end up with a single enormous file
4. Automatically generates cover with title and author (random gradient from 3 harmonious colors)
5. Updates title page and table of contents
6. Creates EPUB file in out/ folder (skipped if `final_clean.txt` is missing)
7. `generate_epub.py` can read plain `.txt` files (e.g., `final_clean.txt` from LanguageTool), so EPUB always uses the latest corrected text

You can explicitly control the cover palette by passing `--cover-colors "#f4f1de,#e07a5f,#3d405b,#81b29a,#f2cc8f"` through `pdf_to_epub.py` or `generate_cover.py`. The five values determine the stripe, upper block, title, and the start+end colors of the lower gradient block, and the author text automatically picks a contrasting color.

Example usage:
```bash
# Full processing with EPUB generation
python pdf_to_epub.py --pdf book.pdf --outdir out --title "Book Title" --author "Author Name" --two-columns --no-oldspelling --lt-cloud --epub-template sample.epub --cover-colors "#f4f1de,#e07a5f,#3d405b,#81b29a,#f2cc8f"

# Or separately (if you already have processed HTML)
python generate_epub.py --template sample.epub --in out/final_better.html --out out/book.epub --title "Book Title" --author "Author Name" --cover-colors "#f4f1de,#e07a5f,#3d405b,#81b29a,#f2cc8f"
```

## Standalone Cover Generation

If you just want to inspect the cover art without running the full pipeline, use `generate_cover.py`. It generates a cover with an upper block, a stripe with a logo, and a gradient lower zone.

### Basic Usage

```bash
python generate_cover.py \
  --title "Book Title" \
  --author "Author Name" \
  --out cover-only.jpg
```

Without specifying colors, the cover will be generated with a random palette.

### Using a 5-Color Palette

You can explicitly set all cover colors via the `--cover-colors` parameter:

```bash
python generate_cover.py \
  --title "Book Title" \
  --author "Author Name" \
  --cover-colors "#8ecae6,#219ebc,#023047,#ffb703,#fb8500" \
  --out cover-only.jpg
```

**Color order (5 HEX values separated by commas):**
1. **Logo stripe** — must be dark, as the logo is white (e.g., `#023047`)
2. **Upper block** — background for author and title (e.g., `#219ebc`)
3. **Title color** — applied directly to the title text (e.g., `#023047`)
4. **Gradient start (lower zone)** — first color of the gradient in the decorative area (e.g., `#ffb703`)
5. **Gradient end (lower zone)** — second color of the gradient (e.g., `#fb8500`)

**Notes:**
- Author name automatically becomes white or black depending on the upper block brightness
- Title color is applied directly without modifications
- Lower zone gradient can be vertical, horizontal, diagonal, or radial (chosen randomly)
- Logo is automatically centered in the stripe and reduced by 10 pixels relative to the stripe height

### Additional Parameters

```bash
python generate_cover.py \
  --title "Book Title" \
  --author "Author Name" \
  --cover-colors "#8ecae6,#219ebc,#023047,#ffb703,#fb8500" \
  --width 1200 \
  --height 1600 \
  --out cover-only.jpg
```

- `--width` — cover width in pixels (default: 1200)
- `--height` — cover height in pixels (default: 1600)

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

Run both steps inside `pdf_to_epub.py` with:
```bash
python pdf_to_epub.py ... --natasha-check --natasha-sync --natasha-out out/sn_natasha.txt --natasha-sync-report out/sn_natasha_sync.txt
```
The flags `--natasha-types`, `--natasha-check`, and `--natasha-sync` sequentially run the Natasha comparison and harmonization before EPUB generation.

Context check:
```bash
python context_checker.py --in out/final_clean.txt --out out/context_warnings.txt --pronouns он,она,оно,они
```
This script uses `pymorphy2` to detect two patterns:
- pronoun + following word (warns when the second token is not parsed as a verb/infinitive),
- adjacent words that should be joined (if `умер шей` produces the valid form `умершей`, it recommends the glued variant).
You can override the pronoun set via `--context-pronouns`.

Enable the context step inside `pdf_to_epub.py`:
```bash
python pdf_to_epub.py ... --context-check --context-out out/context_warnings.txt --natasha-check --natasha-sync
```
`--context-check` runs `context_checker.py` immediately after LanguageTool so the EPUB is built from text that passed the pronoun+verb sanity check.

`pyspellchecker` can be added as another lightweight pass to catch rare typos that LanguageTool misses.

- Features:
- Automatic cover generation with a top block, divider stripe, and gradient-decorated lower block rendered in varying orientations
- The `--cover-colors` option lets you pick the stripe, upper block, title, and lower gradient colors explicitly for both pipeline and standalone cover runs
- Sections numbered starting from 1 (Section0001.xhtml, Section0002.xhtml, etc.)
- Updated title page (Titul.xhtml) with new title and author
- Updated table of contents (toc.ncx) with new sections
- Supports both HTML (final_*.html) and JSON (structured*.json) as source

Repository layout
- pdf_to_epub.py              — orchestrator
- extract_structured_text.py  — structure extraction
- apply_rules_structured.py   — oldspelling rules application
- modernize_structured.py     — modernization and final rendering
- lt_cloud.py                  — LanguageTool (cloud) safe fixes
- post_cleanup.py             — post-cleanup: join spaced letters, fix gaps, Latin→Cyrillic
- generate_epub.py            — EPUB generation from HTML/JSON with automatic cover
- natasha_entity_check.py      — optional named-entity comparison (PER/LOC/ORG) between PDF and final_clean.txt via Natasha
- natasha_sync.py              — harmonize `final_clean.txt` with PDF entity forms via Natasha
- context_checker.py           — context-sensitive pronoun+verb check
- oldspelling.py              — pre‑reform spelling rules (regex map)
- requirements.txt            — dependencies (PyMuPDF, Pillow, natasha)

Publish to GitHub (example)
- cd ocr2epub
- git init -b main
- git add .
- git commit -m "Initial OCR→EPUB toolchain"
- git remote add origin https://github.com/<your-user>/<your-repo>.git
- git push -u origin main

