"""
Локальная проверка орфографии
Поддерживает различные библиотеки: pyspellchecker, jamspell, symspellpy
"""
import argparse
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

# Попытка импортировать различные библиотеки проверки орфографии
SPELLCHECKER_AVAILABLE = False
JAMSPELL_AVAILABLE = False
SYMSPELL_AVAILABLE = False

try:
    from spellchecker import SpellChecker as PySpellChecker
    SPELLCHECKER_AVAILABLE = True
except ImportError:
    try:
        from pyspellchecker import SpellChecker as PySpellChecker
        SPELLCHECKER_AVAILABLE = True
    except ImportError:
        pass

try:
    import jamspell
    JAMSPELL_AVAILABLE = True
except ImportError:
    pass

try:
    import symspellpy
    from symspellpy import SymSpell, Verbosity
    SYMSPELL_AVAILABLE = True
except ImportError:
    pass

try:
    from lt_cloud import SpellChecker, apply_matches, to_html
except ImportError:
    # Если lt_cloud недоступен, определяем базовые функции
    from abc import ABC as SpellCheckerBase
    class SpellChecker(SpellCheckerBase):
        name = "checker"
    
    def apply_matches(text: str, matches) -> str:
        """Apply replacements for each non-overlapping match."""
        matches.sort(key=lambda m: m.get('offset', 0))
        res, i, last_end = [], 0, 0
        for m in matches:
            start = m.get('offset', 0)
            length = m.get('length', 0)
            end = start + length
            if start < last_end:
                continue
            reps = m.get('replacements') or []
            rep = reps[0].get('value') if reps else None
            if rep is None:
                continue
            res.append(text[i:start])
            res.append(rep)
            i = end
            last_end = end
        res.append(text[i:])
        return "".join(res)
    
    def to_html(text: str, title: str) -> str:
        from html import escape as hesc
        return (
            "<!doctype html>\n<html lang=\"ru\">\n<head>\n"
            "<meta charset=\"utf-8\"/>\n"
            f"<title>{hesc(title)}</title>\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"/>\n"
            "<style>body{font:18px/1.6 Georgia,Times,\"Times New Roman\",serif;margin:2rem;max-width:48rem;color:#111;background:#fff} pre{white-space:pre-wrap}</style>\n"
            "</head>\n<body>\n<pre contenteditable=\"true\" spellcheck=\"true\">" + hesc(text) + "</pre>\n</body>\n</html>\n"
        )


WORD_RE = re.compile(r'\b[А-Яа-яёЁ]+\b')


class LocalSpellChecker(SpellChecker):
    """Базовый класс для локальных проверщиков орфографии"""
    name = "LocalSpellChecker"
    
    def __init__(self, lang: str = 'ru'):
        self.lang = lang
    
    @abstractmethod
    def check_word(self, word: str) -> Optional[str]:
        """Проверяет слово и возвращает исправление или None"""
        raise NotImplementedError
    
    def check(self, text: str) -> List[Dict]:
        """Проверяет текст и возвращает список исправлений в формате для apply_matches"""
        matches = []
        for match in WORD_RE.finditer(text):
            word = match.group(0)
            correction = self.check_word(word.lower())
            if correction and correction.lower() != word.lower():
                # Сохраняем регистр первой буквы
                if word[0].isupper():
                    correction = correction.capitalize()
                matches.append({
                    'offset': match.start(),
                    'length': len(word),
                    'replacements': [{'value': correction}],
                    'rule': {'id': 'LOCAL_SPELL', 'description': f'{word} → {correction}'}
                })
        return matches


class PySpellCheckerWrapper(LocalSpellChecker):
    """Обертка для pyspellchecker/spellchecker"""
    name = "PySpellChecker"
    
    def __init__(self, lang: str = 'ru', distance: int = 2):
        super().__init__(lang)
        if not SPELLCHECKER_AVAILABLE:
            raise ImportError("pyspellchecker не установлен. Установите: pip install pyspellchecker")
        # Для русского языка может потребоваться загрузка словаря
        self.spell = PySpellChecker(language=lang, distance=distance)
    
    def check_word(self, word: str) -> Optional[str]:
        """Проверяет слово через pyspellchecker"""
        # pyspellchecker автоматически исправляет слова
        corrected = self.spell.correction(word)
        return corrected if corrected != word else None


class JamSpellWrapper(LocalSpellChecker):
    """Обертка для jamspell"""
    name = "JamSpell"
    
    def __init__(self, model_path: str, lang: str = 'ru'):
        super().__init__(lang)
        if not JAMSPELL_AVAILABLE:
            raise ImportError("jamspell не установлен. Установите: pip install jamspell")
        self.corrector = jamspell.TSpellCorrector()
        if not self.corrector.LoadLangModel(model_path):
            raise ValueError(f"Не удалось загрузить модель jamspell из {model_path}")
    
    def check_word(self, word: str) -> Optional[str]:
        """Проверяет слово через jamspell"""
        corrected = self.corrector.FixFragment(word)
        return corrected if corrected != word else None


class SymSpellWrapper(LocalSpellChecker):
    """Обертка для symspellpy"""
    name = "SymSpell"
    
    def __init__(self, dictionary_path: Optional[str] = None, max_edit_distance: int = 2):
        super().__init__('ru')
        if not SYMSPELL_AVAILABLE:
            raise ImportError("symspellpy не установлен. Установите: pip install symspellpy")
        self.sym_spell = SymSpell(max_dictionary_edit_distance=max_edit_distance, prefix_length=7)
        if dictionary_path:
            if not self.sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1):
                raise ValueError(f"Не удалось загрузить словарь symspell из {dictionary_path}")
        else:
            # Используем встроенный словарь для русского языка
            # Пользователь может создать свой словарь
            pass
    
    def check_word(self, word: str) -> Optional[str]:
        """Проверяет слово через symspellpy"""
        suggestions = self.sym_spell.lookup(word, Verbosity.CLOSEST, max_edit_distance=2)
        if suggestions:
            corrected = suggestions[0].term
            return corrected if corrected != word else None
        return None


def create_spell_checker(checker_type: str = 'auto', **kwargs) -> LocalSpellChecker:
    """
    Создает проверщик орфографии на основе доступных библиотек
    
    Args:
        checker_type: 'auto', 'pyspellchecker', 'jamspell', 'symspell'
        **kwargs: дополнительные параметры для конкретного проверщика
    
    Returns:
        Экземпляр LocalSpellChecker
    """
    if checker_type == 'auto':
        # Автоматический выбор доступной библиотеки
        if SPELLCHECKER_AVAILABLE:
            return PySpellCheckerWrapper(**kwargs)
        elif JAMSPELL_AVAILABLE and 'model_path' in kwargs:
            return JamSpellWrapper(**kwargs)
        elif SYMSPELL_AVAILABLE:
            return SymSpellWrapper(**kwargs)
        else:
            raise ImportError("Ни одна библиотека проверки орфографии не установлена. "
                            "Установите одну из: pyspellchecker, jamspell, symspellpy")
    elif checker_type == 'pyspellchecker':
        return PySpellCheckerWrapper(**kwargs)
    elif checker_type == 'jamspell':
        return JamSpellWrapper(**kwargs)
    elif checker_type == 'symspell':
        return SymSpellWrapper(**kwargs)
    else:
        raise ValueError(f"Неизвестный тип проверщика: {checker_type}")


def run_local_spell_check(text: str, checker: LocalSpellChecker, chunk_size: int = 10000) -> tuple[str, Dict]:
    """
    Применяет локальную проверку орфографии к тексту
    
    Args:
        text: Входной текст
        checker: Экземпляр LocalSpellChecker
        chunk_size: Размер чанка для обработки (не используется для локальных проверщиков)
    
    Returns:
        Кортеж (исправленный текст, статистика)
    """
    matches = checker.check(text)
    fixed_text = apply_matches(text, matches)
    stats = {checker.name: len(matches)}
    return fixed_text, stats


def main():
    ap = argparse.ArgumentParser(
        description='Применить локальную проверку орфографии к тексту'
    )
    ap.add_argument('--in', dest='inp', required=True, help='Входной TXT файл')
    ap.add_argument('--outdir', default='out', help='Папка вывода')
    ap.add_argument('--title', default='Документ (Local Spell)', help='Заголовок HTML')
    ap.add_argument('--checker-type', default='auto', 
                    choices=['auto', 'pyspellchecker', 'jamspell', 'symspell'],
                    help='Тип проверщика орфографии')
    ap.add_argument('--lang', default='ru', help='Язык (по умолчанию ru)')
    ap.add_argument('--model-path', help='Путь к модели (для jamspell)')
    ap.add_argument('--dictionary-path', help='Путь к словарю (для symspell)')
    ap.add_argument('--distance', type=int, default=2, help='Максимальное расстояние редактирования')
    args = ap.parse_args()
    
    inp = Path(args.inp)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Создаем проверщик
    checker_kwargs = {'lang': args.lang}
    if args.checker_type == 'jamspell':
        if not args.model_path:
            print("Ошибка: для jamspell требуется --model-path")
            return
        checker_kwargs['model_path'] = args.model_path
    elif args.checker_type == 'symspell':
        if args.dictionary_path:
            checker_kwargs['dictionary_path'] = args.dictionary_path
        checker_kwargs['max_edit_distance'] = args.distance
    elif args.checker_type == 'pyspellchecker':
        checker_kwargs['distance'] = args.distance
    elif args.checker_type == 'auto' and args.model_path:
        # Если указан model_path и auto, пробуем jamspell
        try:
            checker_kwargs['model_path'] = args.model_path
            checker_kwargs['device'] = args.device
        except:
            pass
    
    try:
        checker = create_spell_checker(args.checker_type, **checker_kwargs)
    except Exception as e:
        print(f"Ошибка создания проверщика: {e}")
        return
    
    # Читаем и обрабатываем текст
    text = inp.read_text(encoding='utf-8', errors='replace')
    fixed_text, stats = run_local_spell_check(text, checker)
    
    # Сохраняем результаты
    (outdir / 'final_local_spell.txt').write_text(fixed_text, encoding='utf-8')
    (outdir / 'final_local_spell.html').write_text(to_html(fixed_text, args.title), encoding='utf-8')
    
    total_fixes = sum(stats.values())
    detail = ", ".join(f"{name}: {count}" for name, count in stats.items())
    print(f'Применено исправлений: {total_fixes} ({detail}). Сохранено final_local_spell.txt/html в {outdir}')


if __name__ == '__main__':
    main()

