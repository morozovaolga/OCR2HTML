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
  - С исправлением через Ollama (рекомендуется, локально, требует установленную Ollama):
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "Мой документ" --ollama
    - python pipeline.py --pdf path/to/file.pdf --outdir out --title "Мой документ" --ollama --ollama-model llama3.1:8b
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
- final_gigachat.txt / final_gigachat.html — после исправления через GigaChat API (грамматика и ошибки OCR с учетом контекста)
- final_ollama.txt / final_ollama.html — после исправления через Ollama (локально, грамматика и ошибки OCR)
- Название_книги.epub — EPUB файл с автоматически сгенерированной обложкой (если указан --epub-template)

Команда и параметры
- python pipeline.py --pdf t1.pdf --outdir output_vol2 --title "t1.pdf (современная, структурированная)" [--no-oldspelling] [--lt-cloud] [--post-clean] [--gigachat] [--ollama] [--ollama-model MODEL] [--two-columns] [--epub-template PATH] [--epub-author AUTHOR]
  - --pdf — путь к PDF
  - --outdir — папка вывода (будет создана)
  - --title — заголовок HTML
  - --no-oldspelling — пропустить применение правил из oldspelling.py
  - --lt-cloud — LanguageTool (облако) — безопасные исправления орфографии и пробелов (без дополнительных зависимостей)
  - --post-clean — пост‑очистка: склейка «В ы р е з к а», «обни мают», латиница→кириллица
  - --gigachat — исправление грамматики и ошибок OCR через GigaChat API (экспериментально, требует переменные окружения GIGACHAT_CLIENT_ID и GIGACHAT_CLIENT_SECRET, может требовать установку сертификатов НУЦ)
  - --ollama — исправление грамматики и ошибок OCR через Ollama (локально, требует установленную Ollama)
  - --ollama-model MODEL — модель Ollama для использования (по умолчанию: mistral:latest)
  - --two-columns — обработка страниц с двумя колонками: сначала все блоки левой колонки (сверху вниз), затем все блоки правой колонки (сверху вниз)
  - --epub-template PATH — путь к шаблону EPUB (например, sample.epub). Если указан, генерирует EPUB из лучшего доступного HTML/JSON. По умолчанию ищет sample.epub в корне проекта
  - --epub-author AUTHOR — имя автора для генерации обложки EPUB

Как работает LanguageTool (--lt-cloud):
LanguageTool — это облачный сервис проверки грамматики и орфографии. В этом проекте используется только для безопасных автоматических исправлений.

Что делает:
1. Отправляет текст частями (по абзацам, до 6000 символов) в облачный API LanguageTool
2. Получает список найденных ошибок и предложенных исправлений
3. Применяет только "безопасные" исправления:
   - Орфографические ошибки (MORFOLOGIK) — например, "машына" → "машина", "карова" → "корова"
   - Пробелы (WHITESPACE, SPACE) — лишние или недостающие пробелы
   - Множественные пробелы (MULTIPLE_SPACES) — "два   пробела" → "два пробела"
   - Двойная пунктуация (DOUBLE_PUNCTUATION) — "??" → "?"
4. Игнорирует стилистические и грамматические правила — только безопасные орфографические исправления
5. Применяет первое предложенное исправление для каждого безопасного совпадения
6. Избегает перекрывающихся исправлений

Что НЕ делает:
- Не исправляет стилистику
- Не меняет грамматику (только орфографию)
- Не исправляет сложные ошибки OCR (например, "ялучше" → "я лучше")
- Не работает с контекстными ошибками

Результат: файлы final_clean.txt и final_clean.html с примененными безопасными исправлениями.

Настройка Ollama (рекомендуется, проще всего):
1. Установите Ollama с https://ollama.com/
2. Загрузите модель (например, mistral:latest):
   ollama pull mistral:latest
3. Убедитесь, что Ollama запущена (обычно запускается автоматически)
4. Используйте флаг --ollama в pipeline.py

Обработка больших файлов через Ollama (фоновый режим):
Обработка больших файлов может занять много времени (часы). Для удобства можно запустить процесс в фоне с логированием.

Вариант 1: Использовать готовые скрипты (рекомендуется)
- PowerShell: .\run_ollama_background.ps1
- BAT файл: run_ollama_background.bat

Эти скрипты запускают процесс в отдельном окне с автоматическим логированием в файл out/ollama_log.txt

Вариант 2: Запуск вручную с логированием
```bash
python ollama_check.py --in out/final_better.txt --outdir out --title "Документ" --model mistral:latest --log-file out/ollama_log.txt
```

Вариант 3: Тестовый режим (обработать только первый кусок)
```bash
python ollama_check.py --in out/final_better.txt --outdir out --title "Документ" --model mistral:latest --test-first
```
После обработки первого куска скрипт спросит, продолжать ли обработку остальных частей.

Проверка прогресса:
- Откройте файл лога: notepad out/ollama_log.txt
- Или следите в реальном времени (PowerShell):
  Get-Content out/ollama_log.txt -Wait -Tail 20

⚠️ ВАЖНО: Компьютер НЕ должен переходить в спящий режим!
Если компьютер перейдет в спящий режим, процесс остановится.

Чтобы предотвратить спящий режим (требует прав администратора):
```powershell
# Отключить спящий режим
powercfg /change standby-timeout-ac 0
powercfg /change standby-timeout-dc 0

# Вернуть обратно (когда закончите обработку)
powercfg /change standby-timeout-ac 30
powercfg /change standby-timeout-dc 15
```

Или настройте в Windows: Панель управления → Электропитание → Изменить параметры плана → Отключить дисплей: Никогда, Переводить компьютер в спящий режим: Никогда

Настройка GigaChat API (экспериментально, может не работать):
⚠️ ВНИМАНИЕ: Подключение к GigaChat API может требовать установку сертификатов НУЦ Минцифры России и дополнительную настройку. Рекомендуется использовать Ollama вместо GigaChat.

Если все же хотите попробовать:
1. Зарегистрируйтесь на https://developers.sber.ru/ и получите Client ID и Client Secret
2. Установите зависимости (если еще не установлены):
   pip install python-dotenv
3. Установите сертификаты НУЦ согласно инструкции на https://developers.sber.ru/docs/ru/gigachat/api/overview
4. Создайте файл .env в корне проекта:
   - Откройте .env и заполните своими значениями:
     GIGACHAT_CLIENT_ID=ваш_client_id
     GIGACHAT_CLIENT_SECRET=ваш_client_secret
     # Или используйте готовый Authorization Key:
     GIGACHAT_AUTH_KEY=ваш_authorization_key_в_base64
   
   Альтернатива: установите переменные окружения в системе:
   - Windows PowerShell:
     $env:GIGACHAT_CLIENT_ID="ваш_client_id"
     $env:GIGACHAT_CLIENT_SECRET="ваш_client_secret"
   - Linux/macOS:
     export GIGACHAT_CLIENT_ID="ваш_client_id"
     export GIGACHAT_CLIENT_SECRET="ваш_client_secret"

Генерация EPUB (--epub-template):
Программа может автоматически создавать EPUB файлы на основе шаблона EPUB и обработанного текста.

Что нужно:
1. Шаблон EPUB файл (например, sample.epub) в корне проекта или указать путь к нему
2. Установленный Pillow: pip install Pillow

Что делает:
1. Использует лучший доступный источник текста (приоритет: final_ollama.html > final_gigachat.html > final_better.html > final_clean.html > final.html)
2. Разбивает текст на разделы (по заголовкам или размеру, до 50 KB на раздел)
3. Автоматически генерирует обложку с названием и автором (случайный градиент из 3 гармоничных цветов)
4. Обновляет титульную страницу и оглавление
5. Создает EPUB файл в папке out/

Пример использования:
```bash
# Полная обработка с генерацией EPUB
python pipeline.py --pdf book.pdf --outdir out --title "Название книги" --two-columns --no-oldspelling --lt-cloud --epub-template sample.epub --epub-author "Имя Автора"

# Или отдельно (если уже есть обработанный HTML)
python generate_epub.py --template sample.epub --in out/final_ollama.html --out out/book.epub --title "Название книги" --author "Имя Автора"
```

Особенности:
- Автоматическая генерация обложки с градиентом из 3 гармоничных цветов
- Разделы нумеруются начиная с 1 (Section0001.xhtml, Section0002.xhtml и т.д.)
- Обновляется титульная страница (Titul.xhtml) с новым заголовком и автором
- Обновляется оглавление (toc.ncx) с новыми разделами
- Поддерживает как HTML (final_*.html), так и JSON (structured*.json) в качестве источника

Структура папки
- pipeline.py — единая точка входа (оркестратор)
- extract_structured_text.py — извлечение блоков/ролей
- apply_rules_structured.py — применение правил oldspelling к структуре
- modernize_structured.py — современная орфография/типографика; HTML/TXT/flags
- lt_cloud.py — безопасные исправления LanguageTool (облако)
- post_cleanup.py — пост‑очистка «буквы через пробел», «обни мают», латиница→кириллица
- gigachat_check.py — исправление грамматики и ошибок OCR через GigaChat API
- ollama_check.py — исправление грамматики и ошибок OCR через Ollama
- generate_epub.py — генерация EPUB из HTML/JSON с автоматической обложкой
- oldspelling.py — правила дореформенной орфографии (regex‑замены)
- requirements.txt — зависимости (PyMuPDF, python-dotenv, Pillow)
- .gitignore — исключения

