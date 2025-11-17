OCR → HTML (с сохранением абзацев и корректурой)

Этот мини‑набор скриптов берёт PDF с уже распознанным (OCR) текстовым слоем, восстанавливает абзацы/заголовки по макету, применяет правила дореформенной орфографии (oldspelling), затем нормализует по современным правилам русской орфографии/типографики и выдаёт финальный HTML/TXT.

Требования
- Python 3.10+
- pip
- Windows/macOS/Linux

Установка (рекомендуется venv)
Windows PowerShell:
- python -m venv .venv
- .\.venv\Scripts\Activate.ps1
- python -m pip install --upgrade pip
- pip install -r requirements.txt

macOS/Linux:
- python3 -m venv .venv
- source .venv/bin/activate
- python -m pip install --upgrade pip
- pip install -r requirements.txt

Быстрый старт
- Подготовьте PDF с уже распознанным текстовым слоем (OCR). Если входной PDF — только картинки, сначала прогоните OCR вне этого проекта (Tesseract/Abbyy и т. п.).
- Запустите конвейер:
  - Базово (сохранение абзацев + корректура):
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "Мой документ (современная версия)"
  - С опциональными шагами:
    - добавить LanguageTool (облако) и пост‑очистку (склейка «В ы р е з к а», «обни мают», латиница→кириллица):
      - python pipeline.py --pdf path/to/file.pdf --outdir out --title "Мой документ" --lt-cloud --post-clean
  - Точечное отключение oldspelling (если не нужно):
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "Без oldspelling" --no-oldspelling
  - Для PDF с двумя колонками на странице (сначала левая, затем правая):
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "Мой документ" --two-columns

Что получится в папке out/
- structured.json — извлечённые блоки текста по страницам (с ролями heading/paragraph)
- structured.html / structured.txt — черновой вывод после структурирования
- structured_rules.json — после применения правил oldspelling ко всем блокам (если не отключено флагом)
- final.html — современная орфография/типографика, аккуратные абзацы (основной HTML)
- final.txt — итоговый текст
- flags.json — пометки неоднозначных замен (для ручной проверки)
Опционально (если включено):
- final_clean.txt / final_clean.html — после безопасных исправлений LanguageTool (облако)
- final_better.txt / final_better.html — после пост‑очистки (склейка букв через пробел, латиница→кириллица)

Команда и параметры
- python pipeline.py --pdf t1.pdf --outdir output_vol2 --title "t1.pdf (современная, структурированная)" [--no-oldspelling] [--lt-cloud] [--post-clean] [--two-columns]
  - --pdf — путь к PDF
  - --outdir — папка вывода (будет создана)
  - --title — заголовок HTML
  - --no-oldspelling — пропустить применение правил из oldspelling.py
  - --lt-cloud — LanguageTool (облако) — безопасные исправления (без дополнительных зависимостей)
  - --post-clean — пост‑очистка: склейка «В ы р е з к а», «обни мают», латиница→кириллица
  - --two-columns — обработка страниц с двумя колонками: сначала все блоки левой колонки (сверху вниз), затем все блоки правой колонки (сверху вниз)

Структура папки
- pipeline.py — единая точка входа (оркестратор)
- extract_structured_text.py — извлечение блоков/ролей
- apply_rules_structured.py — применение правил oldspelling к структуре
- modernize_structured.py — современная орфография/типографика; HTML/TXT/flags
- lt_cloud.py — безопасные исправления LanguageTool (облако)
- post_cleanup.py — пост‑очистка «буквы через пробел», «обни мают», латиница→кириллица
- oldspelling.py — правила дореформенной орфографии (regex‑замены)
- requirements.txt — зависимости (PyMuPDF)
- .gitignore — исключения

