import argparse
import json
import re
import sys
import time
from datetime import datetime
from html import escape as hesc
from pathlib import Path
from typing import List
from urllib import request, parse


def ollama_check(text: str, model: str = "mistral:latest", timeout: int = 120, log_func=None) -> tuple[str, list]:
    """Отправить текст в Ollama для исправления орфографии.
    Возвращает (исправленный_текст, список_спорных_мест)"""
    url = 'http://localhost:11434/api/generate'
    
    # Промпт для исправления орфографии как супер-корректор
    prompt = f"""Ты супер-корректор. Исправь ТОЛЬКО орфографические ошибки в следующем тексте. 

ВАЖНО:
- Исправляй ТОЛЬКО орфографию (правописание слов, склеенные слова, ошибки OCR)
- НЕ трогай стилистику, не меняй слова, не улучшай формулировки
- Сохрани структуру текста, абзацы, пунктуацию, регистр букв
- Если видишь склеенные слова (например, "ялучше" -> "я лучше"), исправь
- Если видишь ошибки OCR (например, "па дитя" -> "на дитя"), исправь
- Если видишь имена собственные, редкие слова, устаревшие формы - НЕ меняй их, даже если они кажутся ошибками
- Если что-то кажется спорным, непонятным, сомнительным - оставь как есть и добавь в список спорных мест

В спорные места включай:
- Имена собственные, которые могут быть ошибками OCR
- Редкие или устаревшие слова
- Фрагменты, где контекст неясен
- Места, где возможны ошибки сканирования, но исправление неочевидно

Верни ответ в формате JSON:
{{
  "corrected_text": "исправленный текст",
  "questionable": [
    {{"original": "исходный фрагмент", "position": "примерное место в тексте", "reason": "почему спорно (имя собственное/ошибка OCR/неясный контекст)"}},
    ...
  ]
}}

Текст для исправления:
{text}"""
    
    payload = {
        'model': model,
        'prompt': prompt,
        'stream': False,
        'options': {
            'temperature': 0.1,
            'num_predict': 2000,  # Ограничиваем длину ответа (меньше для быстрее)
        }
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    
    log = log_func if log_func else (lambda msg: print(msg))
    
    try:
        log(f"    Отправка запроса к Ollama (модель: {model}, размер текста: {len(text)} символов, таймаут: {timeout}с)...")
        start_time = time.time()
        with request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.time() - start_time
            log(f"    Получен ответ за {elapsed:.1f}с, обработка...")
            result = json.loads(resp.read().decode('utf-8', errors='replace'))
            response_text = result.get('response', '').strip()
            
            # Пытаемся распарсить JSON из ответа
            try:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    corrected = parsed.get('corrected_text', text)
                    questionable = parsed.get('questionable', [])
                    log(f"    Обработано, найдено спорных мест: {len(questionable)}")
                    return corrected, questionable
            except Exception as parse_err:
                log(f"    Не удалось распарсить JSON, используем весь ответ как текст")
            
            # Если не удалось распарсить JSON, возвращаем весь ответ как исправленный текст
            return response_text, []
    except Exception as e:
        error_msg = str(e)
        if 'timed out' in error_msg.lower() or 'timeout' in error_msg.lower():
            log(f"    ТАЙМАУТ: запрос не успел завершиться за {timeout}с")
            log(f"    Попробуйте:")
            log(f"    - Увеличить таймаут: --timeout 600")
            log(f"    - Уменьшить размер текста (уже уменьшен до 500 символов)")
            log(f"    - Или использовать более быструю модель")
        else:
            log(f"    ОШИБКА при запросе к Ollama: {e}")
        return text, []


def chunks_by_paragraphs(text: str, max_len: int = 500) -> List[str]:
    """Разбить текст на части по абзацам для обработки.
    Если абзац слишком длинный, разбивает его по предложениям."""
    paras = text.split("\n\n")
    out, buf = [], []
    cur = 0
    
    def split_long_paragraph(para: str, max_size: int) -> List[str]:
        """Разбить длинный абзац на части по предложениям"""
        if len(para) <= max_size:
            return [para]
        
        # Разбиваем по предложениям (точка, восклицательный, вопросительный знак + пробел)
        sentences = re.split(r'([.!?]\s+)', para)
        parts = []
        current = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
            if len(current) + len(sentence) <= max_size:
                current += sentence
            else:
                if current:
                    parts.append(current.strip())
                # Если одно предложение длиннее max_size, разбиваем по запятым
                if len(sentence) > max_size:
                    # Разбиваем по запятым или просто режем
                    comma_parts = re.split(r'([,;]\s+)', sentence)
                    temp = ""
                    for j in range(0, len(comma_parts), 2):
                        chunk = comma_parts[j] + (comma_parts[j+1] if j+1 < len(comma_parts) else "")
                        if len(temp) + len(chunk) <= max_size:
                            temp += chunk
                        else:
                            if temp:
                                parts.append(temp.strip())
                            temp = chunk
                            # Если даже кусок слишком длинный, просто режем
                            while len(temp) > max_size:
                                parts.append(temp[:max_size].strip())
                                temp = temp[max_size:]
                    if temp:
                        parts.append(temp.strip())
                else:
                    current = sentence
        
        if current:
            parts.append(current.strip())
        return parts if parts else [para]
    
    for p in paras:
        if not p.strip():
            continue
            
        # Если абзац слишком длинный, разбиваем его
        if len(p) > max_len:
            split_parts = split_long_paragraph(p, max_len)
            for part in split_parts:
                if cur + len(part) > max_len and buf:
                    out.append("".join(buf))
                    buf, cur = [], 0
                buf.append(part + "\n\n")
                cur += len(part) + 2
        else:
            piece = p + "\n\n"
            if cur + len(piece) > max_len and buf:
                out.append("".join(buf))
                buf, cur = [], 0
            buf.append(piece)
            cur += len(piece)
    
    if buf:
        out.append("".join(buf))
    return out


def to_html(text: str, title: str) -> str:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    body = "\n".join(f"<p>{hesc(p)}</p>" for p in paras)
    return (
        "<!doctype html>\n<html lang=\"ru\">\n<head>\n"
        "<meta charset=\"utf-8\"/>\n"
        f"<title>{hesc(title)}</title>\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/>\n"
        "<style>body{font:18px/1.6 Georgia,Times,\"Times New Roman\",serif;margin:2rem;max-width:48rem;color:#111;background:#fff} p{margin:0 0 1rem}</style>\n"
        "</head>\n<body>\n" + body + "\n</body>\n</html>\n"
    )


def main():
    ap = argparse.ArgumentParser(description='Исправление грамматики и ошибок OCR через Ollama (локально)')
    ap.add_argument('--in', dest='inp', required=True, help='Входной TXT файл')
    ap.add_argument('--outdir', default='out', help='Папка вывода')
    ap.add_argument('--title', default='Документ (Ollama)', help='Заголовок HTML')
    ap.add_argument('--sleep', type=float, default=1.0, help='Пауза между запросами (сек)')
    ap.add_argument('--timeout', type=int, default=300, help='Таймаут HTTP (сек, по умолчанию 300)')
    ap.add_argument('--model', default='mistral:latest', help='Модель Ollama для использования (по умолчанию: mistral:latest)')
    ap.add_argument('--test-first', action='store_true', help='Обработать только первый кусок, сохранить в тестовый файл и ждать подтверждения для продолжения')
    ap.add_argument('--log-file', help='Файл для логирования (если не указан, логи выводятся в консоль)')
    args = ap.parse_args()
    
    # Настройка логирования
    log_file = None
    if args.log_file:
        log_file = Path(args.log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log(message: str, also_print: bool = True):
        """Логировать сообщение в файл и/или консоль"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        if log_file:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_message)
        if also_print:
            print(message)
            sys.stdout.flush()  # Принудительно выводим в консоль
    
    # Проверяем, что Ollama запущена
    try:
        test_req = request.Request('http://localhost:11434/api/tags', method='GET')
        with request.urlopen(test_req, timeout=5) as resp:
            models = json.loads(resp.read().decode('utf-8'))
            available_models = [m['name'] for m in models.get('models', [])]
            if args.model not in available_models:
                print(f"ВНИМАНИЕ: Модель {args.model} не найдена в Ollama.")
                print(f"Доступные модели: {', '.join(available_models)}")
                print(f"Используется: {args.model}")
    except Exception as e:
        print(f"ОШИБКА: Не удалось подключиться к Ollama на localhost:11434")
        print(f"Убедитесь, что Ollama запущена: {e}")
        return 1
    
    inp = Path(args.inp)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    log(f"Используется модель: {args.model}")
    if log_file:
        log(f"Логирование в файл: {log_file}")
    log("Чтение текста...")
    text = inp.read_text(encoding='utf-8', errors='replace')
    parts = chunks_by_paragraphs(text)
    
    log(f"Обработка {len(parts)} частей через Ollama...")
    fixed_parts = []
    all_questionable = []
    
    # Если режим тестирования, обрабатываем только первую часть
    parts_to_process = parts[:1] if args.test_first else parts
    
    for i, part in enumerate(parts_to_process, 1):
        log(f"  Обработка части {i}/{len(parts)}...")
        fixed_part, questionable = ollama_check(part, model=args.model, timeout=args.timeout, log_func=log)
        fixed_parts.append(fixed_part)
        # Добавляем информацию о части к спорным местам
        for q in questionable:
            q['part'] = i
            all_questionable.append(q)
        
        # Если режим тестирования и обработали первую часть
        if args.test_first and i == 1:
            # Сохраняем тестовый результат
            test_text = fixed_part
            test_file = outdir / 'final_ollama_test.txt'
            test_html = outdir / 'final_ollama_test.html'
            test_file.write_text(test_text, encoding='utf-8')
            test_html.write_text(to_html(test_text, args.title + " (тест, часть 1)"), encoding='utf-8')
            
            if all_questionable:
                questionable_text = "СПОРНЫЕ МЕСТА (требуют ручной проверки):\n\n"
                for j, q in enumerate(all_questionable, 1):
                    questionable_text += f"{j}. Часть {q.get('part', '?')}\n"
                    questionable_text += f"   Исходный фрагмент: {q.get('original', '?')}\n"
                    questionable_text += f"   Позиция: {q.get('position', '?')}\n"
                    questionable_text += f"   Причина: {q.get('reason', '?')}\n\n"
                (outdir / 'final_ollama_test_questionable.txt').write_text(questionable_text, encoding='utf-8')
            
            log(f"\n✓ Тестовый результат сохранен:")
            log(f"  - {test_file}")
            log(f"  - {test_html}")
            if all_questionable:
                log(f"  - {outdir / 'final_ollama_test_questionable.txt'}")
            log(f"\nНайдено спорных мест: {len(all_questionable)}")
            log("\n" + "="*60)
            log("Просмотрите результат в файлах final_ollama_test.*")
            log("="*60)
            
            # Ждем подтверждения для продолжения
            response = input("\nПродолжить обработку остальных частей? (да/yes/y или нет/no/n): ").strip().lower()
            if response in ['да', 'yes', 'y', 'д']:
                log("\nПродолжаем обработку...\n")
                # Продолжаем с остальными частями (первая часть уже в fixed_parts)
                for j, remaining_part in enumerate(parts[1:], 2):
                    log(f"  Обработка части {j}/{len(parts)}...")
                    fixed_part, questionable = ollama_check(remaining_part, model=args.model, timeout=args.timeout, log_func=log)
                    fixed_parts.append(fixed_part)
                    for q in questionable:
                        q['part'] = j
                        all_questionable.append(q)
                    if j < len(parts):
                        time.sleep(args.sleep)
            else:
                log("\nОбработка прервана пользователем.")
                log("Тестовый результат сохранен в final_ollama_test.*")
                return 0
        
        if i < len(parts_to_process):
            time.sleep(args.sleep)
    
    fixed_text = "".join(fixed_parts)
    (outdir / 'final_ollama.txt').write_text(fixed_text, encoding='utf-8')
    (outdir / 'final_ollama.html').write_text(to_html(fixed_text, args.title), encoding='utf-8')
    
    # Сохраняем спорные места в отдельный файл
    if all_questionable:
        questionable_text = "СПОРНЫЕ МЕСТА (требуют ручной проверки):\n\n"
        for i, q in enumerate(all_questionable, 1):
            questionable_text += f"{i}. Часть {q.get('part', '?')}\n"
            questionable_text += f"   Исходный фрагмент: {q.get('original', '?')}\n"
            questionable_text += f"   Позиция: {q.get('position', '?')}\n"
            questionable_text += f"   Причина: {q.get('reason', '?')}\n\n"
        (outdir / 'final_ollama_questionable.txt').write_text(questionable_text, encoding='utf-8')
        log(f'Сохранено: final_ollama.txt/html в {outdir}')
        log(f'Сохранено спорных мест: {len(all_questionable)} в final_ollama_questionable.txt')
    else:
        log(f'Сохранено: final_ollama.txt/html в {outdir}')
        log('Спорных мест не обнаружено')
    
    log("Обработка завершена!")


if __name__ == '__main__':
    main()

