OCR → EPUB (paragraph-preserving, with spelling modernization)

This tool processes PDFs with recognized text (OCR), restores document structure (paragraphs/headings), applies pre-reform Russian spelling rules, normalizes to modern Russian spelling/typography, and generates EPUB with an automatically created cover.

Requirements
- Python 3.10+
- pip

Installation
Windows PowerShell:
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

How it works
1. Structure extraction: PDF → JSON with text blocks (heading/paragraph)
2. Pre-reform spelling rules application (oldspelling.py)
3. Modernization: pre-reform → modern Russian spelling/typography
4. Spell checking: LanguageTool (cloud) + Natasha (name synchronization)
5. Context checking: pronoun+verb, split words
6. EPUB generation: chapter splitting, cover creation, table of contents update

Most complete and accurate CLI (79.61% accuracy)
```bash
python pdf_to_epub.py \
  --pdf path/to/file.pdf \
  --outdir out \
  --title "Book Title" \
  --author "Author Name" \
  --lt-cloud \
  --natasha-sync \
  --context-check \
  --epub-template sample.epub
```

Optimal variant (79.61% accuracy, faster)
```bash
python pdf_to_epub.py \
  --pdf path/to/file.pdf \
  --outdir out \
  --title "Book Title" \
  --author "Author Name" \
  --lt-cloud \
  --natasha-sync \
  --epub-template sample.epub
```

Flag explanations

Required:
- `--pdf PATH` — path to PDF file with recognized text
- `--title "Title"` — book title for EPUB
- `--epub-template PATH` — path to EPUB template (default: sample.epub)

Main options:
- `--outdir DIR` — output folder (default: out)
- `--author "Author"` — author name for EPUB cover
- `--two-columns` — PDF with two columns per page
- `--no-oldspelling` — skip pre-reform spelling rules application

Spell checking (recommended):
- `--lt-cloud` — LanguageTool (cloud-based spelling and whitespace checking)
- `--chunk-size N` — chunk size for LanguageTool (default: 6000 characters)
- `--natasha-check` — named entity checking via Natasha (PER, LOC, ORG)
- `--natasha-types TYPES` — entity types (default: PER,LOC)
- `--natasha-out FILE` — check report file (default: natasha_diff.txt)
- `--natasha-sync` — synchronize names from PDF with processed text (+0.19% accuracy)
- `--natasha-sync-report FILE` — synchronization report file (default: natasha_sync.txt)
- `--context-check` — context checking (pronoun+verb, split words)
- `--context-out FILE` — warnings file (default: context_warnings.txt)
- `--context-pronouns LIST` — pronouns for checking (default: он,она,оно,они,мы,вы,ты)

Local spell checking (not recommended):
- `--local-spell` — local checking via pyspellchecker/jamspell/symspell (⚠️ reduces quality to 52.4%)
- `--local-spell-type TYPE` — checker type: pyspellchecker, jamspell, symspell
- `--local-spell-model PATH` — path to model (jamspell) or dictionary (symspell)
- `--local-spell-lang LANG` — checking language (default: ru)

Tokenization:
- `--stanza-tokenize` — improve sentence splitting via Stanza НКРЯ
- `--stanza-model PATH` — path to Stanza model (.pt file)

EPUB:
- `--epub-max-chapter-size KB` — maximum chapter size in KB (default: 50)
- `--epub-use-chapter-heads` — use heading detection for chapter splitting (default: size-based splitting)
- `--cover-colors COLORS` — five HEX colors separated by commas (stripe, upper block, title, gradient start, gradient end)

Test Results
Extended testing of 63 tool combinations with detailed metrics (OCR error types, Precision/Recall/F1, named entity accuracy, structure preservation).

**Results:** [Interactive Dashboard](https://morozovaolga.github.io/ocr2epub/)

**Best Combinations:**
- 🏆 **Maximum Quality:** `--lt-cloud --natasha-sync` (79.61% accuracy, ~8.4 sec)
- ⚡ **Fast Processing:** `--lt-cloud` (79.42% accuracy, ~7 sec)
- 📊 **Base Option:** modernization only (73.90% accuracy, ~1 sec)

**Not Recommended:**
- ❌ `--post-clean` — reduces accuracy (77.27% vs 79.42%)
- ❌ `--local-spell` with pyspellchecker — significantly reduces quality (down to 52.4%)

Output files (in out/)
- `structured.json` — extracted text blocks per page (heading/paragraph)
- `structured.html` / `structured.txt` — preview after structuring
- `structured_rules.json` — after oldspelling rules application
- `final.html` / `final.txt` — modern spelling/typography
- `flags.json` — flagged ambiguous replacements
- `final_clean.txt` / `final_clean.html` — after LanguageTool (if `--lt-cloud`)
- `Book_Title.epub` — EPUB file with automatically generated cover (if `--epub-template`)
