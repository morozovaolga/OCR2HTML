"""
Единый пайплайн от PDF к EPUB
Следует точной схеме из PIPELINE_SCHEMA.md
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Устанавливаем UTF-8 кодировку для консоли (Windows)
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
        os.environ['PYTHONIOENCODING'] = 'utf-8'
    except Exception:
        pass


def run_cmd(cmd, description=""):
    """Запускает команду и выводит описание"""
    if description:
        print(f"\n{'='*80}")
        print(f"{description}")
        print(f"{'='*80}")
    print(f"$ {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Единый пайплайн: PDF → EPUB (по схеме PIPELINE_SCHEMA.md)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

1. Базовый вариант (LanguageTool + Post-cleanup + EPUB):
   python pdf_to_epub.py --pdf book.pdf --title "Название" --author "Автор"

2. С локальной проверкой орфографии:
   python pdf_to_epub.py --pdf book.pdf --title "Название" --author "Автор" \\
     --local-spell --local-spell-type pyspellchecker

3. Максимальная проверка качества:
   python pdf_to_epub.py --pdf book.pdf --title "Название" --author "Автор" \\
     --local-spell --local-spell-type pyspellchecker \\
     --lt-cloud \\
     --context-check \\
     --epub-template sample.epub

4. С кастомными цветами обложки:
   python pdf_to_epub.py --pdf book.pdf --title "Название" --author "Автор" \\
     --cover-colors "#ffbe0b,#fb5607,#ff006e,#8338ec,#3a86ff"
        """
    )
    
    # Основные параметры
    parser.add_argument('--pdf', required=True, help='Путь к PDF файлу')
    parser.add_argument('--outdir', default='out', help='Папка для результатов (по умолчанию: out)')
    parser.add_argument('--title', required=True, help='Название книги')
    parser.add_argument('--author', default='', help='Автор книги')
    
    # Этап 1: Извлечение структуры (обязательно)
    parser.add_argument('--two-columns', action='store_true', help='PDF с двумя колонками на странице')
    
    # Этап 2: Oldspelling (опционально)
    parser.add_argument('--no-oldspelling', action='store_true', help='Пропустить применение правил старой орфографии')
    
    # Этап 3: Stanza токенизация (опционально)
    parser.add_argument('--stanza-tokenize', action='store_true', help='Улучшить разбиение на предложения через Stanza')
    parser.add_argument('--stanza-model', default='', help='Путь к модели Stanza (.pt файл)')
    
    # Этап 4: Модернизация (всегда выполняется)
    
    # Этап 5: Локальная проверка орфографии (опционально)
    parser.add_argument('--local-spell', action='store_true', help='Применить локальную проверку орфографии')
    parser.add_argument('--local-spell-type', default='pyspellchecker', 
                       choices=['pyspellchecker', 'jamspell', 'symspell', 'auto'],
                       help='Тип локального проверщика (по умолчанию: pyspellchecker)')
    parser.add_argument('--local-spell-model', default='', help='Путь к модели (jamspell) или словарю (symspell)')
    parser.add_argument('--local-spell-lang', default='ru', help='Язык для локальной проверки')
    
    # Этап 6: LanguageTool (опционально)
    parser.add_argument('--lt-cloud', action='store_true', help='Использовать LanguageTool (облачная проверка)')
    parser.add_argument('--chunk-size', type=int, default=6000, help='Размер чанка для LanguageTool (по умолчанию: 6000)')
    
    # Этап 7: Контекстная проверка (опционально)
    parser.add_argument('--context-check', action='store_true', help='Контекстная проверка (местоимение+глагол)')
    parser.add_argument('--context-out', default='context_warnings.txt', help='Файл с предупреждениями контекстной проверки')
    parser.add_argument('--context-pronouns', default='он,она,оно,они,мы,вы,ты', help='Местоимения для контекстной проверки')
    
    # Этап 8: Генерация EPUB (опционально)
    parser.add_argument('--epub-template', nargs='?', const='sample.epub', help='Путь к шаблону EPUB (по умолчанию: sample.epub). Если указан, генерирует EPUB')
    parser.add_argument('--cover-colors', default='', help='Пять HEX-цветов через запятую (полоска, верхний блок, заголовок, градиент начало, градиент конец)')
    parser.add_argument('--epub-max-chapter-size', type=int, default=50, help='Максимальный размер главы/секции в KB (по умолчанию: 50)')
    parser.add_argument('--epub-use-chapter-heads', action='store_true', help='Использовать поиск заголовков для разделения на главы (по умолчанию: простое разделение по размеру)')
    
    # Дополнительные проверки (параллельно)
    parser.add_argument('--natasha-check', action='store_true', help='Проверка именованных сущностей через Natasha')
    parser.add_argument('--natasha-types', default='PER,LOC', help='Типы сущностей для Natasha (PER, LOC, ORG)')
    parser.add_argument('--natasha-out', default='natasha_diff.txt', help='Файл отчета Natasha проверки')
    parser.add_argument('--natasha-sync', action='store_true', help='Синхронизация именованных сущностей через Natasha')
    parser.add_argument('--natasha-sync-report', default='natasha_sync.txt', help='Файл отчета Natasha синхронизации')
    
    args = parser.parse_args()
    
    here = Path(__file__).parent
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Проверяем наличие PDF
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"❌ Ошибка: PDF файл не найден: {pdf_path}")
        return 1
    
    print("=" * 80)
    print("ПАЙПЛАЙН: PDF → EPUB")
    print("=" * 80)
    print(f"PDF: {pdf_path}")
    print(f"Название: {args.title}")
    if args.author:
        print(f"Автор: {args.author}")
    print(f"Папка результатов: {outdir}")
    print("\nЭтапы обработки:")
    
    step_num = 1
    
    # Этап 1: Извлечение структуры (обязательно)
    print(f"  {step_num}. Извлечение структуры из PDF")
    step_num += 1
    
    extract_cmd = [
        sys.executable,
        str(here / "extract_structured_text.py"),
        "--pdf", str(pdf_path),
        "--outdir", str(outdir)
    ]
    if args.two_columns:
        extract_cmd.append("--two-columns")
    
    if not run_cmd(extract_cmd, f"Этап 1: Извлечение структуры"):
        return 1
    
    # Определяем входной файл для следующих этапов
    structured_in = outdir / "structured.json"
    
    # Этап 2: Применение правил oldspelling (опционально)
    if not args.no_oldspelling:
        print(f"  {step_num}. Применение правил старой орфографии")
        step_num += 1
        
        apply_cmd = [
            sys.executable,
            str(here / "apply_rules_structured.py"),
            "--rules", str(here / "oldspelling.py"),
            "--in", str(structured_in),
            "--out", str(outdir / "structured_rules.json")
        ]
        if not run_cmd(apply_cmd, f"Этап 2: Применение правил oldspelling"):
            return 1
        
        structured_in = outdir / "structured_rules.json"
    
    # Этап 3: Stanza токенизация (опционально)
    if args.stanza_tokenize and args.stanza_model:
        print(f"  {step_num}. Stanza токенизация")
        step_num += 1
        
        stanza_cmd = [
            sys.executable,
            str(here / "stanza_tokenizer.py"),
            "--in", str(structured_in),
            "--out", str(outdir / "structured_tokenized.json"),
            "--model", args.stanza_model
        ]
        if not run_cmd(stanza_cmd, f"Этап 3: Stanza токенизация"):
            return 1
        
        structured_in = outdir / "structured_tokenized.json"
    
    # Этап 4: Модернизация (всегда выполняется)
    print(f"  {step_num}. Модернизация орфографии")
    step_num += 1
    
    modernize_cmd = [
        sys.executable,
        str(here / "modernize_structured.py"),
        "--in", str(structured_in),
        "--outdir", str(outdir),
        "--title", args.title
    ]
    if not run_cmd(modernize_cmd, f"Этап 4: Модернизация орфографии"):
        return 1
    
    # Определяем входной файл для проверок орфографии
    spell_input = outdir / "final.txt"
    
    # Этап 5: Локальная проверка орфографии (опционально)
    if args.local_spell:
        print(f"  {step_num}. Локальная проверка орфографии ({args.local_spell_type})")
        step_num += 1
        
        if not spell_input.exists():
            print(f"⚠️  Предупреждение: {spell_input.name} не найден — локальная проверка пропущена")
        else:
            local_spell_cmd = [
                sys.executable,
                str(here / "local_spell_checker.py"),
                "--in", str(spell_input),
                "--outdir", str(outdir),
                "--title", args.title + " (Local Spell)",
                "--checker-type", args.local_spell_type,
                "--lang", args.local_spell_lang,
            ]
            if args.local_spell_model:
                if args.local_spell_type == "jamspell":
                    local_spell_cmd.extend(["--model-path", args.local_spell_model])
                elif args.local_spell_type == "symspell":
                    local_spell_cmd.extend(["--dictionary-path", args.local_spell_model])
                elif args.local_spell_type == "auto":
                    local_spell_cmd.extend(["--model-path", args.local_spell_model])
            
            if not run_cmd(local_spell_cmd, f"Этап 5: Локальная проверка орфографии"):
                return 1
            
            # Обновляем входной файл для следующего этапа
            local_spell_output = outdir / "final_local_spell.txt"
            if local_spell_output.exists():
                spell_input = local_spell_output
    
    # Этап 6: LanguageTool (опционально)
    if args.lt_cloud:
        print(f"  {step_num}. LanguageTool проверка")
        step_num += 1
        
        if not spell_input.exists():
            print(f"⚠️  Предупреждение: {spell_input.name} не найден — LanguageTool пропущен")
        else:
            lt_cmd = [
                sys.executable,
                str(here / "lt_cloud.py"),
                "--in", str(spell_input),
                "--outdir", str(outdir),
                "--title", args.title + " (LT)",
                "--chunk-size", str(args.chunk_size),
            ]
            if not run_cmd(lt_cmd, f"Этап 6: LanguageTool проверка"):
                return 1
            
            # Обновляем входной файл для следующего этапа
            lt_output = outdir / "final_clean.txt"
            if lt_output.exists():
                spell_input = lt_output
    
    # Этап 7: Контекстная проверка (опционально)
    if args.context_check:
        print(f"  {step_num}. Контекстная проверка")
        step_num += 1
        
        context_input = outdir / "final_clean.txt"
        if not context_input.exists():
            print(f"⚠️  Предупреждение: {context_input.name} не найден — контекстная проверка пропущена")
        else:
            context_cmd = [
                sys.executable,
                str(here / "context_checker.py"),
                "--in", str(context_input),
                "--out", str(outdir / args.context_out),
                "--pronouns", args.context_pronouns
            ]
            if not run_cmd(context_cmd, f"Этап 7: Контекстная проверка"):
                return 1
    
    # Natasha проверки (параллельно, после LanguageTool)
    if args.natasha_check:
        natasha_input = outdir / "final_clean.txt"
        if natasha_input.exists():
            natasha_cmd = [
                sys.executable,
                str(here / "natasha_entity_check.py"),
                "--pdf", str(pdf_path),
                "--clean", str(natasha_input),
                "--out", str(outdir / args.natasha_out),
                "--types", args.natasha_types
            ]
            run_cmd(natasha_cmd, "Natasha проверка именованных сущностей")
    
    if args.natasha_sync:
        natasha_input = outdir / "final_clean.txt"
        if natasha_input.exists():
            natasha_sync_cmd = [
                sys.executable,
                str(here / "natasha_sync.py"),
                "--pdf", str(pdf_path),
                "--clean", str(natasha_input),
                "--types", args.natasha_types,
                "--report", str(outdir / args.natasha_sync_report)
            ]
            run_cmd(natasha_sync_cmd, "Natasha синхронизация именованных сущностей")
    
    # Этап 8: Генерация EPUB (опционально)
    if args.epub_template:
        print(f"  {step_num}. Генерация EPUB")
        
        # Определяем лучший источник для EPUB (по приоритету из схемы)
        # Приоритет: TXT (чистый обработанный текст) > JSON (структурированные данные) > HTML (может содержать лишнюю разметку)
        epub_sources = [
            outdir / "final_clean.txt",  # Приоритет: обработанный текст выше JSON
            outdir / "final.txt",
            outdir / "structured_rules.json",
            outdir / "structured.json",
            outdir / "final_clean.html",
        ]
        
        epub_source = None
        for source in epub_sources:
            if source.exists():
                # Проверяем, что файл не пустой
                try:
                    is_valid = False
                    if source.suffix.lower() == ".txt":
                        # Для TXT файлов проверяем, что есть достаточно текста (не только пробелы и не только цифры)
                        content = source.read_text(encoding="utf-8").strip()
                        # Проверяем, что есть текст и он не слишком короткий (минимум 50 символов)
                        # И что это не только цифры/пробелы
                        if content and len(content) >= 50:
                            # Проверяем, что есть буквы, а не только цифры
                            has_letters = any(c.isalpha() for c in content)
                            is_valid = has_letters
                        else:
                            is_valid = False
                    elif source.suffix.lower() == ".json":
                        # Для JSON файлов проверяем, что есть блоки
                        data = json.loads(source.read_text(encoding="utf-8"))
                        blocks = data.get("blocks", [])
                        is_valid = bool(blocks and any(b.get("text", "").strip() for b in blocks))
                    elif source.suffix.lower() in (".html", ".htm"):
                        # Для HTML файлов проверяем, что есть контент (не только теги)
                        content = source.read_text(encoding="utf-8")
                        # Убираем все теги и проверяем наличие текста
                        text_only = re.sub(r'<[^>]+>', '', content).strip()
                        # Если HTML содержит только простой текст в <pre> (без структуры),
                        # лучше использовать TXT файл, который будет проверен позже
                        # Проверяем, что это не просто <pre> с текстом
                        if re.search(r'<pre[^>]*>', content, re.IGNORECASE):
                            # Если есть <pre>, проверяем, есть ли другие структурированные элементы
                            has_structure = bool(re.search(r'<(h[1-6]|p|div|section|article|header|footer)[^>]*>', content, re.IGNORECASE))
                            # Если нет структуры, лучше пропустить этот HTML в пользу TXT
                            if not has_structure:
                                is_valid = False  # Пропускаем простой HTML в пользу TXT
                            else:
                                is_valid = bool(text_only)
                        else:
                            is_valid = bool(text_only)
                    
                    if is_valid:
                        epub_source = source
                        break
                    else:
                        # Определяем причину, почему файл был пропущен
                        reason = "пустой"
                        if source.suffix.lower() == ".txt":
                            try:
                                content = source.read_text(encoding="utf-8").strip()
                                if not content:
                                    reason = "пустой"
                                elif len(content) < 50:
                                    reason = f"слишком короткий ({len(content)} символов)"
                                elif not any(c.isalpha() for c in content):
                                    reason = "содержит только цифры/символы"
                            except:
                                reason = "ошибка чтения"
                        print(f"⚠️  Файл {source.name} существует, но {reason} - пропускаем")
                except Exception as e:
                    print(f"⚠️  Предупреждение: ошибка при проверке {source.name}: {e}")
                    continue
        
        if not epub_source:
            print(f"⚠️  Предупреждение: не найден подходящий файл для генерации EPUB")
            print(f"   Проверенные файлы: {', '.join(str(s.name) for s in epub_sources)}")
            # Показываем статус каждого файла
            for source in epub_sources:
                if source.exists():
                    try:
                        size = source.stat().st_size
                        print(f"   - {source.name}: существует ({size} байт)")
                    except:
                        print(f"   - {source.name}: существует (размер неизвестен)")
                else:
                    print(f"   - {source.name}: не найден")
        else:
            print(f"📄 Используется источник для EPUB: {epub_source.name}")
            # Показываем краткую информацию о содержимом
            try:
                if epub_source.suffix.lower() == ".json":
                    import json
                    data = json.loads(epub_source.read_text(encoding="utf-8"))
                    blocks = data.get("blocks", [])
                    blocks_with_text = [b for b in blocks if b.get("text", "").strip()]
                    print(f"   Содержит {len(blocks)} блоков, из них {len(blocks_with_text)} с текстом")
                elif epub_source.suffix.lower() == ".txt":
                    content = epub_source.read_text(encoding="utf-8")
                    lines = [l.strip() for l in content.splitlines() if l.strip()]
                    print(f"   Содержит {len(lines)} непустых строк, размер: {len(content)} символов")
            except Exception as e:
                print(f"   ⚠️  Не удалось проанализировать содержимое: {e}")
            template_epub = Path(args.epub_template)
            if not template_epub.is_absolute():
                if (here / template_epub).exists():
                    template_epub = here / template_epub
                elif (here / "sample.epub").exists():
                    template_epub = here / "sample.epub"
            
            if not template_epub.exists():
                print(f"⚠️  Предупреждение: шаблон EPUB не найден: {template_epub}")
            else:
                # Санитизируем имя файла для Windows (убираем недопустимые символы)
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', args.title)
                safe_title = safe_title.replace(' ', '_')
                output_epub = outdir / f"{safe_title}.epub"
                epub_cmd = [
                    sys.executable,
                    str(here / "generate_epub.py"),
                    "--template", str(template_epub),
                    "--in", str(epub_source),
                    "--out", str(output_epub),
                    "--title", args.title,
                    "--max-chapter-size", str(args.epub_max_chapter_size),
                ]
                if args.author:
                    epub_cmd.extend(["--author", args.author])
                if args.cover_colors:
                    epub_cmd.extend(["--cover-colors", args.cover_colors])
                if args.epub_use_chapter_heads:
                    epub_cmd.append("--use-chapter-heads")
                
                if not run_cmd(epub_cmd, f"Этап 8: Генерация EPUB"):
                    return 1
                
                # Проверяем, создался ли EPUB
                if output_epub.exists():
                    print("\n" + "=" * 80)
                    print("✅ EPUB УСПЕШНО СОЗДАН!")
                    print("=" * 80)
                    print(f"  📚 {output_epub}")
                    print("=" * 80)
    
    print("\n" + "=" * 80)
    print("✅ ОБРАБОТКА ЗАВЕРШЕНА")
    print("=" * 80)
    print(f"Результаты в папке: {outdir}")
    
    # Показываем созданные файлы
    print("\nСозданные файлы:")
    for pattern in ["*.txt", "*.html", "*.json", "*.epub"]:
        files = list(outdir.glob(pattern))
        if files:
            print(f"\n{pattern}:")
            for f in sorted(files):
                print(f"  - {f.name}")
    
    return 0


if __name__ == '__main__':
    exit(main())
