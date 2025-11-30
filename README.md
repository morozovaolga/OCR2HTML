OCR → EPUB (с сохранением абзацев и корректурой)

Этот мини‑набор скриптов берёт PDF с уже распознанным (OCR) текстовым слоем, восстанавливает абзацы/заголовки по макету, применяет правила дореформенной орфографии (oldspelling), затем нормализует по современным правилам русской орфографии/типографики и выдаёт финальный HTML/TXT/EPUB. Основная цель — генерация EPUB файлов с автоматически созданной обложкой на основе шаблона.

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
    - python pdf_to_epub.py --pdf path/to/file.pdf --outdir out --title "Мой документ (современная версия)" --epub-template sample.epub
  - С опциональными шагами:
    - **Рекомендуется:** `--lt-cloud --natasha-sync` для лучшего качества (79.61% точности, ~8.4 сек) — см. [интерактивный дашборд с результатами расширенного тестирования](https://morozovaolga.github.io/ocr2epub/)
    - Быстрый вариант: `--lt-cloud` для хорошего качества (79.42% точности, ~7 сек)
    - ⚠️ **Не рекомендуется:** `--post-clean` (снижает точность до 77.27%) — исключен из расширенного исследования
  - Точечное отключение oldspelling (если не нужно):
    - python pdf_to_epub.py --pdf path/to/file.pdf --outdir out --title "Без oldspelling" --no-oldspelling --epub-template sample.epub
  - Для PDF с двумя колонками на странице (сначала левая, затем правая):
    - python pdf_to_epub.py --pdf path/to/file.pdf --outdir out --title "Мой документ" --two-columns --epub-template sample.epub
  - С генерацией EPUB (требует шаблон EPUB и Pillow):
    - python pdf_to_epub.py --pdf path/to/file.pdf --outdir out --title "Мой документ" --author "Имя Автора" --epub-template sample.epub
  - С моделями НКРЯ для улучшенной вычитки:
    - python pdf_to_epub.py --pdf path/to/file.pdf --outdir out --title "Мой документ" --lt-cloud --stanza-tokenize --stanza-model path/to/tokenizer.pt --epub-template sample.epub

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
  - python pdf_to_epub.py --pdf t1.pdf --outdir output_vol2 --title "t1.pdf (современная, структурированная)" [--no-oldspelling] [--lt-cloud] [--chunk-size N] [--post-clean] [--two-columns] [--epub-template PATH] [--author AUTHOR] [--epub-max-chapter-size KB]
  - --pdf — путь к PDF
  - --outdir — папка вывода (будет создана)
  - --title — название книги (для HTML и EPUB)
  - --no-oldspelling — пропустить применение правил из oldspelling.py
  - --lt-cloud — LanguageTool (облако) — безопасные исправления орфографии и пробелов (без дополнительных зависимостей)
  - --local-spell — применить локальную проверку орфографии (pyspellchecker/jamspell/symspellpy) перед LanguageTool
  - --local-spell-type — тип локального проверщика: auto, pyspellchecker, jamspell, symspell (по умолчанию auto)
  - --local-spell-model — путь к модели (для jamspell) или словарю (для symspell)
  - --local-spell-lang — язык для локальной проверки (по умолчанию ru)
  - --chunk-size — максимальное количество символов в одном запросе LanguageTool (по умолчанию 6000)
  - --post-clean — пост‑очистка: склейка «В ы р е з к а», «обни мают», латиница→кириллица (⚠️ не рекомендуется: снижает точность до 77.27% против 79.42% с LanguageTool)
  - --two-columns — обработка страниц с двумя колонками: сначала все блоки левой колонки (сверху вниз), затем все блоки правой колонки (сверху вниз)
  - --epub-template PATH — путь к шаблону EPUB (например, sample.epub). Если указан, генерирует EPUB из лучшего доступного HTML/JSON. По умолчанию ищет sample.epub в корне проекта (перед генерацией должен существовать `final_clean.txt`, иначе EPUB пропускается)
  - --epub-max-chapter-size KB — максимальный размер главы (в килобайтах) при генерации EPUB (по умолчанию 50 KB); если в тексте нет явно отмеченных заголовков, главы разбиваются по размеру
  - --cover-colors COLORS — пять HEX-цветов в порядке: полоска с логотипом, верхний блок, заголовок, начало градиента нижней зоны и конец градиента. Авторский текст выбирается белым или чёрным, чтобы контрастировать с верхним блоком.
  - --author AUTHOR — имя автора для генерации обложки EPUB
  - --natasha-types TYPES — типы сущностей для Natasha (`PER`, `LOC`, `ORG`). По умолчанию `PER,LOC`.
  - --natasha-check — запустить сравнение именованных сущностей между PDF и `final_clean.txt` с помощью Natasha
  - --natasha-out FILE — имя файла отчёта (по умолчанию `natasha_diff.txt`, создаётся в папке вывода)
  - --natasha-sync — гармонизировать `final_clean.txt` с упоминаниями из PDF (замены PER/LOC/ORG)
  - --natasha-sync-report FILE — отчёт о применённых заменах (по умолчанию `natasha_sync.txt` в папке вывода)
  - --context-check — контекстная проверка (`он шелк`, несовпадения местоимение+глагол) через pymorphy2
  - --context-out FILE — файл с предупреждениями контекстной проверки (по умолчанию `context_warnings.txt`)
  - --context-pronouns LIST — через запятую разделённый список местоимений (по умолчанию `он,она,оно,они,мы,вы,ты`)
  - --stanza-tokenize — улучшить разбиение на предложения с помощью токенизатора Stanza НКРЯ
  - --stanza-model PATH — путь к модели Stanza (.pt файл). Скачайте с https://ruscorpora.ru/license-content/neuromodels
- --natasha-check — запустить сравнение именованных сущностей между PDF и `final_clean.txt` с помощью Natasha (PER/LOC/ORG)
- --natasha-out FILE — имя файла отчёта (по умолчанию `natasha_diff.txt`, создаётся в выходной папке)

Как работает LanguageTool:
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

Результат: применение LanguageTool даёт безопасную проверку орфографии и пробелов.

### Локальная проверка орфографии

Для работы без интернета или для дополнительной проверки можно использовать локальные модели проверки орфографии. Локальная проверка выполняется **перед** LanguageTool, что позволяет комбинировать оба подхода для максимальной точности.

Поддерживаемые библиотеки:

1. **pyspellchecker** — простая библиотека на основе расстояния Левенштейна:
   ```bash
   pip install pyspellchecker
   python pdf_to_epub.py --pdf book.pdf --local-spell --local-spell-type pyspellchecker --epub-template sample.epub
   ```

2. **jamspell** — более точная модель с поддержкой контекста (требует модель):
   ```bash
   pip install jamspell
   python pdf_to_epub.py --pdf book.pdf --local-spell --local-spell-type jamspell --local-spell-model path/to/model.bin --epub-template sample.epub
   ```

3. **symspellpy** — быстрая проверка на основе симметричного удаления (требует словарь):
   ```bash
   pip install symspellpy
   python pdf_to_epub.py --pdf book.pdf --local-spell --local-spell-type symspell --local-spell-model path/to/dictionary.txt --epub-template sample.epub
   ```


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
5. Автоматически генерирует обложку с верхним блоком, полоской и градиентной нижней зоной — текст автора и названия выровнен и оттипографлен.
6. По желанию можно задать точную палитру через `--cover-colors "#f4f1de,#e07a5f,#3d405b,#81b29a,#f2cc8f"` (первые три цвета для полоски, верхнего блока и заголовка, последние два — для градиента нижней области).
7. Обновляет титульную страницу и оглавление
8. Создает EPUB файл в папке out/

Пример использования:
```bash
# Полная обработка с генерацией EPUB
python pdf_to_epub.py --pdf book.pdf --outdir out --title "Название книги" --author "Имя Автора" --two-columns --no-oldspelling --lt-cloud --epub-template sample.epub

# Или отдельно (если уже есть обработанный HTML)
python generate_epub.py --template sample.epub --in out/final_better.html --out out/book.epub --title "Название книги" --author "Имя Автора"
```

## Генерация обложки отдельно

Если хочется сразу увидеть обложку, не запуская весь pipeline, используйте `generate_cover.py`. Он генерирует обложку с верхним блоком, полоской с логотипом и градиентной нижней зоной.

### Базовое использование

```bash
python generate_cover.py \
  --title "Название книги" \
  --author "Имя Автора" \
  --out cover-only.jpg
```

Без указания цветов обложка будет сгенерирована со случайной палитрой.

### Использование с палитрой из 5 цветов

Можно явно задать все цвета обложки через параметр `--cover-colors`:

```bash
python generate_cover.py \
  --title "Название книги" \
  --author "Имя Автора" \
  --cover-colors "#8ecae6,#219ebc,#023047,#ffb703,#fb8500" \
  --out cover-only.jpg
```

**Порядок цветов (5 HEX-значений через запятую):**
1. **Полоска с логотипом** — должна быть тёмной, так как логотип белый (например, `#023047`)
2. **Верхний блок** — фон для автора и заголовка (например, `#219ebc`)
3. **Цвет заголовка** — применяется напрямую к тексту заголовка (например, `#023047`)
4. **Начало градиента нижней зоны** — первый цвет градиента в декоративной части (например, `#ffb703`)
5. **Конец градиента нижней зоны** — второй цвет градиента (например, `#fb8500`)

**Важно:**
- Имя автора автоматически становится белым или чёрным в зависимости от яркости верхнего блока
- Цвет заголовка применяется напрямую, без модификаций
- Градиент нижней зоны может быть вертикальным, горизонтальным, диагональным или радиальным (выбирается случайно)
- Логотип автоматически центрируется в полоске и уменьшается на 10 пикселей относительно высоты полоски

### Дополнительные параметры

```bash
python generate_cover.py \
  --title "Название" \
  --author "Автор" \
  --cover-colors "#8ecae6,#219ebc,#023047,#ffb703,#fb8500" \
  --width 1200 \
  --height 1600 \
  --out cover-only.jpg
```

- `--width` — ширина обложки в пикселях (по умолчанию 1200)
- `--height` — высота обложки в пикселях (по умолчанию 1600)

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

Или добавьте автоматический шаг в `pdf_to_epub.py`:
```bash
python pdf_to_epub.py ... --natasha-check --natasha-sync --natasha-out out/sn_natasha.txt --natasha-sync-report out/sn_natasha_sync.txt
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

Или включите контекстную проверку в `pdf_to_epub.py`:
```bash
python pdf_to_epub.py ... --context-check --context-out out/context_warnings.txt --natasha-check --natasha-sync
```
`--context-check` запускает `context_checker.py` сразу после LanguageTool, ещё до пост‑очистки и генерации EPUB.

Дополнительно: `pyspellchecker` можно использовать как новый этап после LT (отдельным скриптом) — он хорошо ловит редкие слова и очевидные опечатки, но не заменяет морфологический разбор.

Модели НКРЯ для улучшенной вычитки:
Проект поддерживает интеграцию нейросетевых моделей из [Национального корпуса русского языка](https://ruscorpora.ru/license-content/neuromodels) для более точной вычитки текстов после OCR.

### Токенизатор Stanza

Улучшает разбиение текста на предложения и токены (точность 95.6% для предложений, 99.6% для токенов).

**Что нужно:**
1. Установить зависимость: `pip install stanza~=1.8.1`
2. Скачать модель токенизатора с [страницы НКРЯ](https://ruscorpora.ru/license-content/neuromodels) (файл .pt, ~641KB)
3. Принять лицензионное соглашение НКРЯ

**Использование:**
```bash
# В pdf_to_epub.py
python pdf_to_epub.py --pdf book.pdf --outdir out --title "Книга" --stanza-tokenize --stanza-model path/to/tokenizer.pt --epub-template sample.epub

# Отдельно
python stanza_tokenizer.py --in out/structured.json --out out/structured_tokenized.json --model path/to/tokenizer.pt
```

Токенизатор применяется после извлечения структуры, но до модернизации орфографии, что улучшает качество разбиения предложений и помогает пост-очистке.


Особенности:
- Автоматическая генерация обложки с верхним блоком, полоской, текстом и градиентной декоративной зоной, причем графика может рендериться в разных ориентациях (вертикальный, горизонтальный, диагональный, радиальный)
- Можно явно задать палитру через `--cover-colors`, чтобы управлять каждой зоной обложки (полоска, верхний блок, заголовок и градиент)
- Разделы нумеруются начиная с 1 (Section0001.xhtml, Section0002.xhtml и т.д.)
- Обновляется титульная страница (Titul.xhtml) с новым заголовком и автором
- Обновляется оглавление (toc.ncx) с новыми разделами
- Поддерживает как HTML (final_*.html), так и JSON (structured*.json) в качестве источника

Сравнение PDF ↔ clean_txt (опционально)
 - compare_pdf_clean_names.py — сравнивает именованные фразы между PDF (современная орфография) и `final_clean.txt`, показывает расхождения.
 - natasha_entity_check.py — извлекает сущности типа PER/LOC/ORG через Natasha и сравнивает их между PDF и `final_clean.txt`, отчёт сохраняет `natasha_diff.txt`

Структура папки
- pdf_to_epub.py — единая точка входа (оркестратор)
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
- stanza_tokenizer.py — улучшенная токенизация с помощью модели Stanza НКРЯ
- oldspelling.py — правила дореформенной орфографии (regex‑замены)
- requirements.txt — зависимости (PyMuPDF, Pillow, natasha, stanza, pyspellchecker, symspellpy)
- .gitignore — исключения

