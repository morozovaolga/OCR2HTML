import argparse
import json
import os
import re
import time
from html import escape as hesc
from pathlib import Path
from typing import List
from urllib import request, parse

# Загружаем переменные окружения из .env файла, если он есть
try:
    from dotenv import load_dotenv
    load_dotenv()  # Загружаем переменные из .env файла в корне проекта
except ImportError:
    pass  # python-dotenv не установлен, используем только системные переменные окружения


def get_access_token(client_id: str = None, client_secret: str = None, auth_key: str = None) -> str:
    """Получить токен доступа от GigaChat API
    
    Можно использовать либо:
    - client_id и client_secret (будут закодированы в base64)
    - auth_key (уже закодированный Authorization Key в base64)
    """
    url = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
    data = parse.urlencode({
        'scope': 'GIGACHAT_API_PERS'
    }).encode('utf-8')
    
    req = request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    req.add_header('Accept', 'application/json')
    req.add_header('RqUID', 'unique-request-id-' + str(int(time.time())))
    
    # Базовая авторизация
    if auth_key:
        # Используем готовый Authorization Key (уже в base64)
        req.add_header('Authorization', f'Basic {auth_key}')
    elif client_id and client_secret:
        # Кодируем Client ID:Client Secret в base64
        import base64
        credentials = f"{client_id}:{client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        req.add_header('Authorization', f'Basic {encoded_credentials}')
    else:
        raise ValueError("Необходимо указать либо auth_key, либо client_id и client_secret")
    
    try:
        import ssl
        # Создаем SSL контекст с правильными настройками для сертификатов НУЦ
        context = ssl.create_default_context()
        # Разрешаем TLS 1.2 и выше (требуется для GigaChat API)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        with request.urlopen(req, timeout=30, context=context) as resp:
            payload = resp.read().decode('utf-8', errors='replace')
            result = json.loads(payload)
            return result.get('access_token', '')
    except request.HTTPError as e:
        # Получаем детали ошибки из ответа сервера
        error_body = ''
        try:
            if hasattr(e, 'fp') and e.fp:
                error_body = e.fp.read().decode('utf-8', errors='replace')
            elif hasattr(e, 'read'):
                error_body = e.read().decode('utf-8', errors='replace')
        except:
            pass
        
        print(f"Ошибка получения токена: HTTP {e.code} {e.reason}")
        if error_body:
            print(f"Ответ сервера: {error_body}")
        else:
            print("Ответ сервера пустой. Проверьте:")
            print("  1. Правильность Client ID и Client Secret в файле .env")
            print("  2. Что ключи не содержат лишних пробелов или кавычек")
        return ''
    except Exception as e:
        print(f"Ошибка получения токена: {e}")
        return ''


def gigachat_check(text: str, access_token: str, timeout: int = 60) -> tuple[str, list]:
    """Отправить текст в GigaChat для исправления орфографии через прямой HTTP запрос.
    Возвращает (исправленный_текст, список_спорных_мест)"""
    url = 'https://gigachat.devices.sberbank.ru/api/v1/chat/completions'
    
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
        'model': 'GigaChat',
        'messages': [
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'temperature': 0.1,
        'max_tokens': 4000
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {access_token}')
    
    try:
        import ssl
        # Создаем SSL контекст с правильными настройками для сертификатов НУЦ
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        with request.urlopen(req, timeout=timeout, context=context) as resp:
            result = json.loads(resp.read().decode('utf-8', errors='replace'))
            if 'choices' in result and len(result['choices']) > 0:
                response_text = result['choices'][0]['message']['content'].strip()
                
                # Пытаемся распарсить JSON из ответа
                try:
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                        corrected = parsed.get('corrected_text', text)
                        questionable = parsed.get('questionable', [])
                        return corrected, questionable
                except:
                    pass
                
                return response_text, []
            return text, []
    except Exception as e:
        print(f"Ошибка при запросе к GigaChat: {e}")
        return text, []


def chunks_by_paragraphs(text: str, max_len: int = 3000) -> List[str]:
    """Разбить текст на части по абзацам для обработки"""
    paras = text.split("\n\n")
    out, buf = [], []
    cur = 0
    for p in paras:
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
    ap = argparse.ArgumentParser(description='Исправление грамматики и ошибок OCR через GigaChat API')
    ap.add_argument('--in', dest='inp', required=True, help='Входной TXT файл')
    ap.add_argument('--outdir', default='out', help='Папка вывода')
    ap.add_argument('--title', default='Документ (GigaChat)', help='Заголовок HTML')
    ap.add_argument('--sleep', type=float, default=1.0, help='Пауза между запросами (сек)')
    ap.add_argument('--timeout', type=int, default=60, help='Таймаут HTTP (сек)')
    args = ap.parse_args()
    
    # Получаем учетные данные из переменных окружения
    # Можно использовать либо готовый Authorization Key, либо Client ID + Secret
    auth_key = os.getenv('GIGACHAT_AUTH_KEY')
    client_id = os.getenv('GIGACHAT_CLIENT_ID')
    client_secret = os.getenv('GIGACHAT_CLIENT_SECRET')
    
    if not auth_key and (not client_id or not client_secret):
        print("ОШИБКА: Необходимо установить переменные окружения")
        print("\nВариант 1 (проще): Используйте готовый Authorization Key")
        print("  В файле .env добавьте:")
        print("  GIGACHAT_AUTH_KEY=ваш_authorization_key_в_base64")
        print("\nВариант 2: Используйте Client ID и Client Secret")
        print("  В файле .env добавьте:")
        print("  GIGACHAT_CLIENT_ID=ваш_client_id")
        print("  GIGACHAT_CLIENT_SECRET=ваш_client_secret")
        print("\nПолучите ключи на https://developers.sber.ru/")
        return 1
    
    inp = Path(args.inp)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    print("Получение токена доступа...")
    if auth_key:
        access_token = get_access_token(auth_key=auth_key)
    else:
        access_token = get_access_token(client_id=client_id, client_secret=client_secret)
    if not access_token:
        print("ОШИБКА: Не удалось получить токен доступа.")
        return 1
    
    print("Чтение текста...")
    text = inp.read_text(encoding='utf-8', errors='replace')
    parts = chunks_by_paragraphs(text)
    
    print(f"Обработка {len(parts)} частей через GigaChat...")
    fixed_parts = []
    all_questionable = []
    for i, part in enumerate(parts, 1):
        print(f"  Обработка части {i}/{len(parts)}...")
        fixed_part, questionable = gigachat_check(part, access_token, timeout=args.timeout)
        fixed_parts.append(fixed_part)
        # Добавляем информацию о части к спорным местам
        for q in questionable:
            q['part'] = i
            all_questionable.append(q)
        if i < len(parts):
            time.sleep(args.sleep)
    
    fixed_text = "".join(fixed_parts)
    (outdir / 'final_gigachat.txt').write_text(fixed_text, encoding='utf-8')
    (outdir / 'final_gigachat.html').write_text(to_html(fixed_text, args.title), encoding='utf-8')
    
    # Сохраняем спорные места в отдельный файл
    if all_questionable:
        questionable_text = "СПОРНЫЕ МЕСТА (требуют ручной проверки):\n\n"
        for i, q in enumerate(all_questionable, 1):
            questionable_text += f"{i}. Часть {q.get('part', '?')}\n"
            questionable_text += f"   Исходный фрагмент: {q.get('original', '?')}\n"
            questionable_text += f"   Позиция: {q.get('position', '?')}\n"
            questionable_text += f"   Причина: {q.get('reason', '?')}\n\n"
        (outdir / 'final_gigachat_questionable.txt').write_text(questionable_text, encoding='utf-8')
        print(f'Сохранено: final_gigachat.txt/html в {outdir}')
        print(f'Сохранено спорных мест: {len(all_questionable)} в final_gigachat_questionable.txt')
    else:
        print(f'Сохранено: final_gigachat.txt/html в {outdir}')
        print('Спорных мест не обнаружено')


if __name__ == '__main__':
    main()

