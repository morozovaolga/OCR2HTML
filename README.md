OCR → HTML (с сохранением абзацев и корректурой)

Этот мини‑набор скриптов берёт PDF с уже распознанным (OCR) текстовым слоем, восстанавливает абзацы/заголовки по макету, применяет правила дореформенной орфографии (oldspelling), затем нормализует по современным правилам русской орфографии/типографики и выдаёт финальный HTML/TXT. Также поддерживает генерацию EPUB файлов с автоматически созданной обложкой на основе шаблона.

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
- (опционально) для GigaChat: pip install python-dotenv

macOS/Linux:
- python3 -m venv .venv
- source .venv/bin/activate
- python -m pip install --upgrade pip
- pip install -r requirements.txt
- (опционально) для GigaChat: pip install python-dotenv

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
  - С генерацией EPUB (требует шаблон EPUB и Pillow):
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "Мой документ" --epub-template sample.epub --epub-author "Имя Автора"

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
- Название_книги.epub — EPUB файл с автоматически сгенерированной обложкой (если указан --epub-template)

Команда и параметры
  - python pipeline.py --pdf t1.pdf --outdir output_vol2 --title "t1.pdf (современная, структурированная)" [--no-oldspelling] [--lt-cloud] [--with-yandex] [--yandex-lang LANG] [--chunk-size N] [--post-clean] [--two-columns] [--epub-template PATH] [--epub-author AUTHOR] [--epub-max-chapter-size KB]
  - --pdf — путь к PDF
  - --outdir — папка вывода (будет создана)
  - --title — заголовок HTML
  - --no-oldspelling — пропустить применение правил из oldspelling.py
  - --lt-cloud — LanguageTool (облако) — безопасные исправления орфографии и пробелов (без дополнительных зависимостей)
  - --with-yandex — дополнительно прогонять текст через Yandex.Speller (простой орфографический чек после LanguageTool)
  - --yandex-lang — язык для Yandex.Speller (по умолчанию ru)
  - --chunk-size — максимальное количество символов в одном запросе LanguageTool/Yandex (по умолчанию 6000)
  - --post-clean — пост‑очистка: склейка «В ы р е з к а», «обни мают», латиница→кириллица
  - --two-columns — обработка страниц с двумя колонками: сначала все блоки левой колонки (сверху вниз), затем все блоки правой колонки (сверху вниз)
  - --epub-template PATH — путь к шаблону EPUB (например, sample.epub). Если указан, генерирует EPUB из лучшего доступного HTML/JSON. По умолчанию ищет sample.epub в корне проекта (перед генерацией должен существовать `final_clean.txt`, иначе EPUB пропускается)
  - --epub-max-chapter-size KB — максимальный размер главы (в килобайтах) при генерации EPUB (по умолчанию 50 KB); если в тексте нет явно отмеченных заголовков, главы разбиваются по размеру
  - --epub-author AUTHOR — имя автора для генерации обложки EPUB
  - --natasha-types TYPES — типы сущностей для Natasha (`PER`, `LOC`, `ORG`). По умолчанию `PER,LOC`.
  - --natasha-check — запустить сравнение именованных сущностей между PDF и `final_clean.txt` с помощью Natasha
  - --natasha-out FILE — имя файла отчёта (по умолчанию `natasha_diff.txt`, создаётся в папке вывода)
  - --natasha-sync — гармонизировать `final_clean.txt` с упоминаниями из PDF (замены PER/LOC/ORG)
  - --natasha-sync-report FILE — отчёт о применённых заменах (по умолчанию `natasha_sync.txt` в папке вывода)
  - --context-check — контекстная проверка (`он шелк`, несовпадения местоимение+глагол) через pymorphy2
  - --context-out FILE — файл с предупреждениями контекстной проверки (по умолчанию `context_warnings.txt`)
  - --context-pronouns LIST — через запятую разделённый список местоимений (по умолчанию `он,она,оно,они,мы,вы,ты`)
- --natasha-check — запустить сравнение именованных сущностей между PDF и `final_clean.txt` с помощью Natasha (PER/LOC/ORG)
- --natasha-out FILE — имя файла отчёта (по умолчанию `natasha_diff.txt`, создаётся в выходной папке)

Как работает LanguageTool и Yandex.Speller:
LanguageTool — это облачный сервис проверки грамматики и орфографии. В этом проекте используется только для безопасных автоматических исправлений, без сложной стилистики и грамматики.

Что делает:
1. Отправляет текст частями (по абзацам, по умолчанию до 6000 символов, регулируется через `--chunk-size`) в облачный API LanguageTool
2. Получает список найденных ошибок и предложенных исправлений
3. Применяет только "безопасные" исправления:
   - Орфографические ошибки (MORFOLOGIK) — например, "машына" → "машина", "карова" → "корова"
   - Пробелы (WHITESPACE, SPACE) — лишние или недостающие пробелы
   - Множественные пробелы (MULTIPLE_SPACES) — "два   пробела" → "два пробела"
   - Двойная пунктуация (DOUBLE_PUNCTUATION) — "??" → "?"
4. После каждого блока применяет только первое безопасное исправление и избегает пересекающихся изменений
5. Дополнительно (по флагу `--with-yandex`) прогоняет результат через Yandex.Speller — простой орфографический сервис, который ловит базовые опечатки (можно указать язык `--yandex-lang`)

Результат: последовательное применение LanguageTool и, при желании, Yandex.Speller даёт безопасную, двухуровневую проверку орфографии и пробелов.

Что НЕ делает:
- Не исправляет стилистику
- Не меняет грамматику (только орфографию)
- Не исправляет сложные ошибки OCR (например, "ялучше" → "я лучше")
- Не работает с контекстными ошибками

Результат: файлы final_clean.txt и final_clean.html с примененными безопасными исправлениями.

Генерация EPUB (--epub-template):
Программа может автоматически создавать EPUB файлы на основе шаблона EPUB и обработанного текста.

Что нужно:
1. Шаблон EPUB файл (например, sample.epub) в корне проекта или указать путь к нему
2. Установленный Pillow: pip install Pillow

Что делает:
1. Использует лучший доступный источник текста (приоритет: final_better.html > final_clean.txt > final_clean.html > final.txt > structured_rules.json > structured.json)
2. `generate_epub.py` умеет читать `.txt`, поэтому EPUB строится по итоговому `final_clean.txt`, если он появился после LanguageTool
3. При обработке `.txt` специальные строки в начале абзаца считаются заголовками: `Часть`, `Глава`, `Раздел`, `Книга` (с цифрой), `***` или римские числа. Это позволяет разбить текст на главы без готовой HTML-структуры.
4. Разбивает текст на разделы (по заголовкам или размеру, до 50 KB на раздел)
5. Автоматически генерирует обложку с названием и автором (случайный градиент из 3 гармоничных цветов)
6. Обновляет титульную страницу и оглавление
7. Создает EPUB файл в папке out/

Пример использования:
```bash
# Полная обработка с генерацией EPUB
python pipeline.py --pdf book.pdf --outdir out --title "Название книги" --two-columns --no-oldspelling --lt-cloud --epub-template sample.epub --epub-author "Имя Автора"

# Или отдельно (если уже есть обработанный HTML)
python generate_epub.py --template sample.epub --in out/final_better.html --out out/book.epub --title "Название книги" --author "Имя Автора"
```

Дополнительная проверка имен собственных:
```bash
python compare_pdf_clean_names.py --pdf makar/makar.pdf --clean out/final_clean.txt --modern-pdf --out out/name_diff.txt
```
Скрипт ищет фразы, начинающиеся с заглавных слов (например, `Глава I`, `Часть IV`, `Имя`) в PDF и `final_clean.txt` и записывает несовпадения для ручной проверки.

Natasha (NER) для более насыщенной проверки:
```bash
python natasha_entity_check.py --pdf sn.pdf --clean out/final_clean.txt --out out/sn_natasha.txt --types PER,LOC,ORG
```
Утилита извлекает сущности типов `PER`, `LOC`, `ORG` через Natasha и сравнивает их нормализованные формы между PDF и `final_clean.txt`. Отчёт сохраняет только те сущности, которые есть в одном файле и отсутствуют в другом. Параметр `--types` позволяет убрать или добавить конкретные типы сущностей (например, оставить только `PER` и `LOC`).

Гармонизация финального текста по Наташе:
```bash
python natasha_sync.py --pdf sn.pdf --clean out/final_clean.txt --report out/sn_natasha_sync.txt --types PER,LOC,ORG
```
Скрипт заменяет в `final_clean.txt` все вариации сущностей (PER/LOC/ORG), которые встретились и в PDF, но были приведены к иным формам после модернизации. После этого EPUB можно заново построить, и имена/географии точно совпадают с оригиналом.

Или добавьте автоматический шаг в `pipeline.py`:
```bash
python pipeline.py ... --natasha-check --natasha-sync --natasha-out out/sn_natasha.txt --natasha-sync-report out/sn_natasha_sync.txt
```
Флаги `--natasha-types`, `--natasha-check`, `--natasha-sync` и связанные отчёты управляют последовательным запуском проверки и гармонизации после LanguageTool.

Контекстная проверка:
```bash
python context_checker.py --in out/final_clean.txt --out out/context_warnings.txt --pronouns он,она,оно,они
```
Скрипт использует `pymorphy2`, несколько правил:  
1) «местоимение + следующее слово» — если второе слово не распознаётся как глагол/инфинитив, появляется предупреждение;  
2) «склеивание соседних слов» — если два слова `умер шей` дают нормальную форму `умершей`, он предлагает объединить их до склейки.  
Можно настраивать список местоимений через `--context-pronouns`.

Или включите контекстную проверку в `pipeline.py`:
```bash
python pipeline.py ... --context-check --context-out out/context_warnings.txt --natasha-check --natasha-sync
```
`--context-check` запускает `context_checker.py` сразу после LanguageTool, ещё до пост‑очистки и генерации EPUB.

Дополнительно: `pyspellchecker` можно использовать как новый этап после LT (отдельным скриптом) — он хорошо ловит редкие слова и очевидные опечатки, но не заменяет морфологический разбор.

Особенности:
- Автоматическая генерация обложки с градиентом из 3 гармоничных цветов
- Обложка генерируется с несколькими стилями градиента (вертикальный, горизонтальный, диагональный, радиальный) и слоями паттернов (кружки, полосы) для вариативного дизайна
- Разделы нумеруются начиная с 1 (Section0001.xhtml, Section0002.xhtml и т.д.)
- Обновляется титульная страница (Titul.xhtml) с новым заголовком и автором
- Обновляется оглавление (toc.ncx) с новыми разделами
- Поддерживает как HTML (final_*.html), так и JSON (structured*.json) в качестве источника

Сравнение PDF ↔ clean_txt (опционально)
 - compare_pdf_clean_names.py — сравнивает именованные фразы между PDF (современная орфография) и `final_clean.txt`, показывает расхождения.
 - natasha_entity_check.py — извлекает сущности типа PER/LOC/ORG через Natasha и сравнивает их между PDF и `final_clean.txt`, отчёт сохраняет `natasha_diff.txt`

Структура папки
 - pipeline.py — единая точка входа (оркестратор)
 - extract_structured_text.py — извлечение блоков/ролей
 - apply_rules_structured.py — применение правил oldspelling к структуре
 - modernize_structured.py — современная орфография/типографика; HTML/TXT/flags
 - lt_cloud.py — безопасные исправления LanguageTool (облако)
 - post_cleanup.py — пост‑очистка «буквы через пробел», «обни мают», латиница→кириллица
- generate_epub.py — генерация EPUB из HTML/JSON с автоматической обложкой
- compare_pdf_clean_names.py — дополнительная проверка имен собственных между PDF и final_clean.txt
- natasha_entity_check.py — проверка именованных сущностей (PER/LOC/ORG) через Natasha
- natasha_sync.py — гармонизация `final_clean.txt` по сущностям из PDF
- context_checker.py — контекстная проверка местоимение+глагол
 - oldspelling.py — правила дореформенной орфографии (regex‑замены)
 - requirements.txt — зависимости (PyMuPDF, python-dotenv, Pillow)
 - .gitignore — исключения

