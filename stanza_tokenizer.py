"""
Токенизатор на основе Stanza (модель НКРЯ)
Улучшает разбиение текста на предложения и токены после OCR.
"""
import argparse
import json
from pathlib import Path
from typing import List, Dict

try:
    import stanza
except ImportError:
    print("Ошибка: stanza не установлен. Установите: pip install stanza~=1.8.1")
    print("Также нужно скачать модель НКРЯ с https://ruscorpora.ru/license-content/neuromodels")
    raise


# Глобальная переменная для кэширования pipeline
_cached_pipeline = None
_cached_model_path = None

def get_stanza_pipeline(model_path: str, use_gpu: bool = False):
    """
    Получить или создать Stanza pipeline (кэшируется для переиспользования).
    
    Args:
        model_path: Путь к модели .pt файлу
        use_gpu: Использовать ли GPU (если доступен)
    
    Returns:
        Stanza Pipeline объект
    """
    global _cached_pipeline, _cached_model_path
    
    # Если pipeline уже загружен для этой модели, используем его
    if _cached_pipeline is not None and _cached_model_path == model_path:
        return _cached_pipeline
    
    # Загружаем новую модель
    _cached_pipeline = stanza.Pipeline(
        lang='ru',
        processors='tokenize',
        tokenize_model_path=model_path,
        use_gpu=use_gpu
    )
    _cached_model_path = model_path
    return _cached_pipeline


def tokenize_with_stanza(text: str, model_path: str, use_gpu: bool = False) -> List[Dict]:
    """
    Токенизирует текст с помощью модели Stanza НКРЯ.
    
    Args:
        text: Входной текст
        model_path: Путь к модели .pt файлу
        use_gpu: Использовать ли GPU (если доступен)
    
    Returns:
        Список словарей с информацией о предложениях и токенах
    """
    pipeline = get_stanza_pipeline(model_path, use_gpu)
    
    doc = pipeline(text)
    result = []
    
    for sentence in doc.sentences:
        tokens = [token.text for token in sentence.tokens]
        result.append({
            'sentence': sentence.text,
            'tokens': tokens,
            'start_char': sentence.tokens[0].start_char if sentence.tokens else 0,
            'end_char': sentence.tokens[-1].end_char if sentence.tokens else 0,
        })
    
    return result


def process_text_file(input_file: Path, output_file: Path, model_path: str, use_gpu: bool = False):
    """
    Обрабатывает текстовый файл: улучшает разбиение на предложения.
    """
    text = input_file.read_text(encoding='utf-8', errors='ignore')
    
    # Разбиваем на абзацы для сохранения структуры
    paragraphs = text.split('\n\n')
    processed_paragraphs = []
    
    for para in paragraphs:
        if not para.strip():
            processed_paragraphs.append(para)
            continue
        
        # Токенизируем абзац
        try:
            sentences_data = tokenize_with_stanza(para, model_path, use_gpu)
            # Собираем предложения обратно
            sentences = [s['sentence'] for s in sentences_data]
            processed_paragraphs.append(' '.join(sentences))
        except Exception as e:
            print(f"Ошибка при обработке абзаца: {e}")
            # В случае ошибки оставляем оригинал
            processed_paragraphs.append(para)
    
    result_text = '\n\n'.join(processed_paragraphs)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(result_text, encoding='utf-8')
    
    return result_text


def process_json_file(input_file: Path, output_file: Path, model_path: str, use_gpu: bool = False):
    """
    Обрабатывает JSON файл со структурированными блоками: улучшает разбиение предложений в каждом блоке.
    """
    data = json.loads(input_file.read_text(encoding='utf-8'))
    
    # Поддерживаем два формата: список блоков или словарь с ключом "blocks"
    if isinstance(data, dict):
        blocks = data.get('blocks', [])
    elif isinstance(data, list):
        blocks = data
    else:
        raise ValueError(f"Неожиданный формат JSON: ожидается dict или list, получен {type(data)}")
    
    # Загружаем pipeline один раз для всех блоков
    print(f"Загрузка модели Stanza: {model_path}")
    pipeline = get_stanza_pipeline(model_path, use_gpu)
    print("Модель загружена, начинаю обработку блоков...")
    
    processed_blocks = []
    total_blocks = len(blocks)
    
    for idx, block in enumerate(blocks, 1):
        # Проверяем, что block - это словарь
        if not isinstance(block, dict):
            print(f"⚠️  Пропущен блок {idx}/{total_blocks} неверного формата: {type(block)}")
            processed_blocks.append(block)
            continue
            
        if block.get('role') == 'heading':
            # Заголовки не трогаем
            processed_blocks.append(block)
            continue
        
        text = block.get('text', '')
        if not text.strip():
            processed_blocks.append(block)
            continue
        
        try:
            # Используем уже загруженный pipeline
            doc = pipeline(text)
            sentences = [sentence.text for sentence in doc.sentences]
            block['text'] = ' '.join(sentences)
            processed_blocks.append(block)
            
            if idx % 10 == 0:
                print(f"Обработано блоков: {idx}/{total_blocks}")
        except Exception as e:
            print(f"Ошибка при обработке блока {idx}/{total_blocks}: {e}")
            processed_blocks.append(block)
    
    print(f"Обработка завершена: {len(processed_blocks)} блоков")
    
    # Сохраняем в том же формате, что и входной файл
    if isinstance(data, dict):
        data['blocks'] = processed_blocks
        output_data = data
    else:
        output_data = processed_blocks
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding='utf-8')
    
    return processed_blocks


def main():
    parser = argparse.ArgumentParser(
        description="Улучшенная токенизация текста с помощью модели Stanza НКРЯ"
    )
    parser.add_argument("--in", dest="input_file", required=True, help="Входной файл (.txt или .json)")
    parser.add_argument("--out", required=True, help="Выходной файл")
    parser.add_argument(
        "--model",
        required=True,
        help="Путь к модели Stanza (.pt файл). Скачайте с https://ruscorpora.ru/license-content/neuromodels"
    )
    parser.add_argument("--gpu", action="store_true", help="Использовать GPU (если доступен)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input_file)
    output_path = Path(args.out)
    model_path = Path(args.model)
    
    if not input_path.exists():
        print(f"Ошибка: входной файл не найден: {input_path}")
        return 1
    
    if not model_path.exists():
        print(f"Ошибка: модель не найдена: {model_path}")
        print("Скачайте модель с https://ruscorpora.ru/license-content/neuromodels")
        return 1
    
    if input_path.suffix == '.json':
        process_json_file(input_path, output_path, str(model_path), args.gpu)
    else:
        process_text_file(input_path, output_path, str(model_path), args.gpu)
    
    print(f"Токенизация завершена. Результат сохранён в {output_path}")
    return 0


if __name__ == "__main__":
    exit(main())

